# Hermes · Notion 本地工具

原生模型提供商参考实现，提供 `claude-sonnet5.5` 与 `claude-opus5.5`。工具执行由 Hermes 管理，插件负责请求与回复转换，不修改 Hermes 核心，不另开 HTTP 服务。

先使用仓库首页的[“复制以下内容给 agent 安装”](../README.md#复制以下内容给-agent-安装)，由 agent 与用户明确目标客户端和 profile。选择 Hermes 后，再按本文操作。

## 兼容范围

开发时验证环境为 macOS、Hermes `v0.22.1+243.g8b9ac57`、OpenAI SDK `2.24.0`。两个模型已做过独立 profile 的真实文件读写与字节核对；仓库仅提供代码和方法，不附私人日志、测试文件或截图。另一台电脑仍需重新验收。

实现依赖该版本的 `ProviderProfile.create_client()`。不同版本必须先核对本机源码/官方文档，不能靠修改核心或忽略兼容检查强行安装。当前适用于 `in_process`；不支持 `plugins.isolation: host` 返回活客户端的场景，不能为了安装而擅自降低用户原有隔离设置。

## 安装步骤

1. 与用户确认 Hermes、实际 profile 和测试工作目录。核对版本及现有插件，备份将修改的文件；保留原默认模型与其他连接信息。
2. 优先建立空白测试 profile，不复制私人历史、消息渠道或业务任务。当前版本示例：

   ```bash
   hermes profile create notion-tools-test --no-skills --no-alias
   ```

   `notion-tools-test` 只是示例名称，已存在时使用新名称。新建 profile 可能带有初始默认模型，也可能被现有 gateway 自动发现；不要假定它完全不受当前运行环境影响。

3. 克隆本仓库，在目标 profile 的 Hermes home 下创建 `plugins/model-providers/notion-local-tools/`，**只复制**本目录的三个文件：

   ```text
   __init__.py
   notion_bridge.py
   plugin.yaml
   ```

   默认 home 通常为 `~/.hermes`，命名 profile 通常在其 `profiles/` 下；实际路径以用户本机设置为准，不要假定默认 home 就是所选 profile。建议在发现目录外准备完整文件后原子移入，避免加载半份插件。

   **不要直接运行 `hermes plugins install 5483666/dsh-notion-local-tools`。** 这是多客户端仓库，仓库根目录是 DSH 包；Hermes 插件位于 `hermes/`。当前提供手动目录安装方法，没有宣称根仓库可由 Hermes 插件安装器直接安装。

4. 让用户在本机私密输入请求地址和 key，使用该版本 Hermes 原生私密设置服务，写入所选 profile 的两个专用连接项：

   ```text
   NOTION_LOCAL_TOOLS_BASE_URL
   NOTION_LOCAL_TOOLS_API_KEY
   ```

   该版本的 `hermes_cli.config.save_env_value()` 可在**已绑定正确 profile 的 Hermes 运行时**内带锁追加；调用前核对 API、目标 home、变量冲突，并让用户通过本机不回显输入提供值。本文不提供带真实值的命令，不要求把值发到聊天里。私有 `.env` 使用 `0600` 或系统等价权限，保留原内容；有同名连接项时先确认归属，不能覆盖。Hermes 在所选 profile 私密保存后无需每次重新输入；这与 DSH 每次启动输入的向导不同。

5. 检查发现、凭据解析和模型目录。可在能访问 Hermes CLI 的环境中校验源码目录：

   ```bash
   hermes -p notion-tools-test plugins validate ./hermes
   ```

   从本仓库根目录运行以上示例。原生提供商的 `fallback_models` 与 `fetch_models()` 只暴露两个模型，无需请求上游完整目录。不能只填写 `providers:` 就假定生效：注册提供商与自定义路由可能有不同的地址解析优先级。

6. 为测试会话选择新提供商，先验收再接入用户确认的常用 profile；每个 profile 分别安装，不改变其原默认模型。例如：

   ```bash
   hermes -p notion-tools-test chat --provider notion-local-tools --model claude-sonnet5.5
   ```

   在 Desktop 模型菜单可选择 **Notion · 本地工具 → Sonnet5.5 / Opus5.5**。运行中的 backend 是否热发现，取决于版本；未出现时先定位加载/缓存问题，再协调只重开必要会话或 backend，不重启全部业务任务。

## 适配思路

代码入口：[`__init__.py`](__init__.py)、[`notion_bridge.py`](notion_bridge.py)。

- 提供商声明模型能力，`create_client()` 提供自定义客户端；敏感连接信息由 Hermes 按 profile 解析后传入，模块导入时不缓存 home 或读取其他 profile 的环境。
- `encode_request()` 把 system、历史、工具 schema、call ID 和实际工具结果合入一条 user 文本；上游按用户选定的模型调用。
- `decode_reply()` 只接受完整协议 JSON，验证本轮声明的工具名和 `tool_choice`，再转换成 Hermes 可消费的 OpenAI `tool_calls` 或文本结果。
- 同步 worker 和异步辅助请求都保留自定义 transport。特别要验证标题、压缩等异步路径，避免宿主重新构造普通 SDK 客户端而绕过适配。
- 非法地址在自定义 transport 本地拒绝；不在工厂中抛出校验异常，避免宿主捕获后回退普通客户端。错误正文经过替换，不回显上游敏感内容。

完整的跨客户端设计与验收步骤见 [PORTING.md](../docs/PORTING.md)。官方扩展契约参考 [Hermes Model Provider Plugins](https://github.com/NousResearch/hermes-agent/blob/8b9ac5773ea07189f23aa9dfcdba1e59fd759c21/website/docs/developer-guide/model-provider-plugin.md)。

## 测试

在能够 import **用户当前 Hermes 源码及其匹配依赖**的 Python 环境中，从仓库根目录运行：

```bash
python -m unittest discover -s hermes/tests -v
```

打包版 Hermes 的依赖可能隔离在自己的运行时；不要假定系统 `python` 就可运行。agent 应先定位该安装的实际运行时，或在独立开发环境准备匹配的 Hermes，避免升级系统 Python 或改动核心来凑环境。

八项自动化测试无需提供真实连接信息，测试代码使用假 key，网络调用仅针对本机临时 HTTP 夹具；建议在空白测试 profile 或隔离运行时执行。包含 Hermes 客户端工厂与异步转换路径的测试，因此不是仅安装 OpenAI SDK 就能跑完的通用 Python 测试。

真实验收另行在空白工作区执行：生成随机 `input.txt`，模型仅用客户端原生读写工具创建 `output.txt` 并回读，外部独立比较字节，包括末尾换行。每个模型、客户端、系统的结论分别记录；不得把目录可见或单元测试通过当成真实读写完成。

## 限制与回滚

仅文本。上游完整返回后合成 SDK 流事件，不是逐 token 上游流。异步 HTTP 使用工作线程，取消等待后已发出的请求可能继续至超时；单个网络阶段最多 120 秒。同步调用按 Hermes 标准路径在 worker 执行，在 asyncio 中需 `await`；不支持第三方在事件循环线程中强行同步调用的混合用法。用量/费用未知时不要把缺失值当作准确统计。

其他系统、复杂并发、host 隔离与长期稳定性尚未验收。上游认证、限流和 502 等仍可能失败。

回滚前先把使用此提供商的会话切至其他模型，再移除新增插件目录和确认属于本插件的两个连接项。保留其他 `.env` 内容与 `config.yaml`，不要用旧备份覆盖用户后续修改。
