import json
import asyncio
import importlib.util
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import openai

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notion_bridge import create_client

TOOLS = [{"type": "function", "function": {"name": "read_file", "description": "Read a local file", "parameters": {
    "type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.status = 200
        self.reply = '{"tool_calls":[{"name":"read_file","arguments":{"path":"input.txt"}}]}'
        self.raw = None
        self.stall = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['content-length'])))
                owner.requests.append((self.path, dict(self.headers), body))
                if owner.stall:
                    self.send_response(200)
                    self.send_header('content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"choices":')
                    self.wfile.flush()
                    threading.Event().wait(0.3)
                    return
                data = owner.raw if owner.raw is not None else json.dumps({
                    "id": "upstream-fixture", "object": "chat.completion", "created": 1,
                    "model": body['model'], "choices": [{"index": 0, "message": {"role": "assistant", "content": owner.reply}, "finish_reason": "stop"}]
                }).encode()
                self.send_response(owner.status)
                self.send_header('content-type', 'application/json')
                self.send_header('content-length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = create_client(base_url=f'http://127.0.0.1:{self.server.server_port}/v1', api_key='fixture-key', max_retries=0)

    def tearDown(self):
        asyncio.run(self.client.aclose())
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def call(self, **kwargs):
        return self.client.chat.completions.create(model='claude-sonnet5.5', tools=TOOLS,
            messages=[{'role': 'user', 'content': 'Read input.txt'}], **kwargs)

    def test_native_sdk_tool_calls_preserve_full_history_on_one_upstream_user_message(self):
        result = self.client.chat.completions.create(model='claude-opus5.5', tools=TOOLS, messages=[
            {'role': 'system', 'content': 'Keep local file permissions'},
            {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'previous_call', 'type': 'function', 'function': {'name': 'read_file', 'arguments': '{"path":"input.txt"}'}}]},
            {'role': 'tool', 'tool_call_id': 'previous_call', 'content': 'nonce-from-disk'},
            {'role': 'user', 'content': 'Continue'}])
        self.assertEqual(result.choices[0].finish_reason, 'tool_calls')
        self.assertEqual(result.choices[0].message.tool_calls[0].function.name, 'read_file')
        self.assertEqual(json.loads(result.choices[0].message.tool_calls[0].function.arguments), {'path': 'input.txt'})
        path, headers, body = self.requests[0]
        self.assertEqual(path, '/v1/chat/completions')
        self.assertEqual(body['model'], 'claude-opus5.5')
        self.assertFalse(body['stream'])
        self.assertEqual(len(body['messages']), 1)
        self.assertEqual(body['messages'][0]['role'], 'user')
        self.assertIn('previous_call', body['messages'][0]['content'])
        self.assertIn('nonce-from-disk', body['messages'][0]['content'])
        self.assertIn('Keep local file permissions', body['messages'][0]['content'])
        self.assertNotIn('tools', body)

    def test_streaming_is_consumable_by_real_openai_sdk(self):
        with self.call(stream=True) as stream:
            chunks = list(stream)
        calls = [call for c in chunks for call in c.choices[0].delta.tool_calls or []]
        self.assertEqual(calls[0].function.name, 'read_file')
        self.assertEqual(chunks[-1].choices[0].finish_reason, 'tool_calls')
        self.reply = '{"text":"Verified local output"}'
        with self.call(stream=True) as stream:
            chunks = list(stream)
        self.assertEqual(''.join(c.choices[0].delta.content or '' for c in chunks), 'Verified local output')
        self.assertEqual(chunks[-1].choices[0].finish_reason, 'stop')

    def test_prose_unknown_tools_and_images_fail_closed(self):
        for reply in ['example: {"tool_calls":[{"name":"read_file","arguments":{}}]}',
                      '{"tool_calls":[{"name":"shell","arguments":{"cmd":"echo bad"}}]}',
                      '{"text":"done","tool_calls":[{"name":"read_file","arguments":{}}]}']:
            self.reply = reply
            with self.assertRaises(openai.APIStatusError):
                self.call()
        count = len(self.requests)
        with self.assertRaises(openai.APIStatusError):
            self.client.chat.completions.create(model='claude-sonnet5.5', messages=[{'role': 'user', 'content': [
                {'type': 'image_url', 'image_url': {'url': 'https://example.com/private-image'}}]}])
        self.assertEqual(len(self.requests), count)

    def test_upstream_error_bodies_are_sanitized_and_status_preserved(self):
        self.status = 401
        self.raw = b'{"error":{"message":"sensitive-upstream-body-and-fixture-key"}}'
        with self.assertRaises(openai.AuthenticationError) as caught:
            self.call()
        self.assertNotIn('sensitive-upstream-body', str(caught.exception))
        self.assertEqual(caught.exception.status_code, 401)

    def test_hermes_async_auxiliary_conversion_keeps_the_bridge(self):
        from agent.auxiliary_client import _to_async_client
        self.reply = '{"text":"async verified"}'

        async def exercise():
            client, model = _to_async_client(self.client, 'claude-sonnet5.5')
            try:
                response = await client.chat.completions.create(model=model, messages=[{'role': 'user', 'content': 'Hello'}])
                self.assertEqual(response.choices[0].message.content, 'async verified')
                stream = await client.chat.completions.create(model=model, messages=[{'role': 'user', 'content': 'Hello'}], stream=True)
                chunks = [chunk async for chunk in stream]
                self.assertEqual(''.join(chunk.choices[0].delta.content or '' for chunk in chunks), 'async verified')
            finally:
                if client is not self.client:
                    await client.close()

        asyncio.run(exercise())
        self.assertTrue(all('HERMES_REQUEST_JSON' in row[2]['messages'][0]['content'] for row in self.requests))

    def test_invalid_endpoint_cannot_trigger_hermes_plain_client_fallback(self):
        from types import SimpleNamespace
        from agent.agent_runtime_helpers import _provider_supplied_client
        path = Path(__file__).resolve().parents[1] / '__init__.py'
        spec = importlib.util.spec_from_file_location('notion_test_plugin', path, submodule_search_locations=[str(path.parent)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        client = _provider_supplied_client(SimpleNamespace(provider='notion-local-tools'), {
            'api_key': 'fixture-key', 'base_url': f'http://127.0.0.1:{self.server.server_port}/v1?private=query', 'max_retries': 0})
        self.assertIsNotNone(client, 'provider construction must not fall back to a plain client')
        try:
            with self.assertRaises(openai.BadRequestError):
                client.chat.completions.create(model='claude-sonnet5.5', messages=[{'role': 'user', 'content': 'Hello'}])
            self.assertEqual(self.requests, [])
        finally:
            client.close()

    def test_body_read_timeout_remains_a_transport_timeout(self):
        self.stall = True
        with self.assertRaises(openai.APITimeoutError):
            self.call(timeout=0.05)

    def test_forbidden_or_required_tool_choice_is_enforced(self):
        with self.assertRaises(openai.APIStatusError):
            self.call(tool_choice='none')
        self.reply = '{"text":"not a tool"}'
        with self.assertRaises(openai.APIStatusError):
            self.call(tool_choice='required')


if __name__ == '__main__':
    unittest.main()
