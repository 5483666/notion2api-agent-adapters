"""Native Hermes model provider. Private connection settings live in each profile."""
from providers import register_provider
from providers.base import ProviderProfile
from .notion_bridge import MODELS, create_client


class NotionLocalToolsProfile(ProviderProfile):
    def create_client(self, **client_kwargs):
        return create_client(**client_kwargs)

    def fetch_models(self, **kwargs):
        # Only expose models covered by this bridge, without a remote directory request.
        return list(MODELS)


register_provider(NotionLocalToolsProfile(
    name='notion-local-tools', display_name='Notion · 本地工具',
    description='Notion text bridge with local tools executed by Hermes',
    api_mode='chat_completions', auth_type='api_key',
    env_vars=('NOTION_LOCAL_TOOLS_API_KEY', 'NOTION_LOCAL_TOOLS_BASE_URL'),
    base_url='', fallback_models=MODELS, default_aux_model='claude-sonnet5.5',
    supports_vision=False, supports_vision_tool_messages=False,
    model_capabilities={model: {'supports_tools': True, 'supports_vision': False,
                               'supports_reasoning': False, 'context_window': 100_000} for model in MODELS},
))
