# notion2api · 各类 Agent 本地工具适配

供 agent 或开发者把用户自己的 notion2api 接口适配到其电脑上的客户端，实现真实本地文件读写。先与用户明确目标客户端，再按其当前扩展接口操作。

本仓库提供通用适配方法和 Hermes 参考实现，保留 Sonnet 5.5 / Opus 5.5。DSH 插件在独立仓库维护，此处不存放 DSH 插件。

| 内容 | 入口 |
| --- | --- |
| Hermes 提供商源码、安装、测试与回滚 | [Hermes 说明](hermes/README.md) |
| 通用协议、客户端入口与验收方法 | [适配指南](docs/PORTING.md) |
| DSH 插件（独立仓库） | [dsh-notion-local-tools](https://github.com/5483666/dsh-notion-local-tools) |

**OpenCode、pi 尚无本仓库可直接安装的实现，未完成实机验收。** 需要按各自当前接口适配，不能直接安装 Hermes 插件。

只公开代码、虚构测试夹具和说明，不包含真实服务器 IP、请求地址、API key、Notion cookie、私人 profile、会话、验收记录或备份。地址和密钥由使用者在自己的电脑上私密配置。

## 复制以下内容给 agent 安装

复制下面整段。先确认目标客户端，再安装或适配；真实地址和密钥由用户在本机私密输入。

```text
请根据这个仓库，在我自己的电脑上安装或适配 notion2api 本地工具：
https://github.com/5483666/notion2api-agent-adapters

第一步先问我：这次要适配哪个客户端（DSH、Hermes、OpenCode、pi 或其他）？等我明确确认后再安装或改配置，不要按你自己的运行环境或仓库名猜测，也不要同时修改其他客户端。

确认目标后，读取仓库 README、对应客户端说明及 docs/PORTING.md，核对本机版本、实际 profile 和工作目录。Hermes 使用本仓库已有实现；若选择 DSH，转到 https://github.com/5483666/dsh-notion-local-tools 。其他客户端按当前官方接口适配，不能把“有参考代码”当成“已支持”。不兼容时先说明。

保留现有配置、默认模型与权限，修改前备份，不中断现有任务。保留 Sonnet 5.5 和 Opus 5.5 选项；请求地址和 API key 让我在本机私密输入，按对应客户端的私密连接机制处理，不要写入聊天、日志或公开内容。

先在独立 profile 或测试目录，用真实客户端工具完成读取随机 input.txt、写入 output.txt、回读确认；模型不用 shell，独立比较文件字节与末尾换行。通过后再接入我确认的常用配置。

最后说明安装位置、启动或选模型的方法、实际验收范围与回滚方式；无法完成的部分如实说明。
```

## 获取源码

```bash
git clone https://github.com/5483666/notion2api-agent-adapters.git
cd notion2api-agent-adapters
```

确认目标是 Hermes 后，按 [Hermes 安装说明](hermes/README.md) 操作；插件位于 `hermes/` 子目录，不能把仓库根目录直接交给 Hermes 插件安装器。其他客户端请阅读[通用适配方法](docs/PORTING.md)。

MIT License。欢迎在自己的分支适配其他客户端；请注明实际验证的版本、系统与模型，勿提交私有连接信息或验收记录。
