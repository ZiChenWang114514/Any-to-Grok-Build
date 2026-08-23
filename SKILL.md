---
name: codex-grok-build
description: 在用户要求安装、登录、检查、启动、继续、监督、压缩或排查 Grok Build CLI 会话时使用；覆盖 Windows PowerShell、受控无头调用、会话状态、上下文维护、真实验证和精确清理。不用于把 Grok 注册成 Codex 原生子 Agent 或 API Provider。
---

# Codex Grok Build

将 Grok Build 作为本机外部编码协作者使用。Codex 负责确认任务、工作目录和已有改动，Grok 在用户授权的目录中实施，Codex 随后独立验证结果。

## 默认参数

辅助脚本从 [references/defaults.json](references/defaults.json) 读取请求超时、冒烟测试超时、上下文提醒值和测试回复。不要在脚本或说明中复制这些数值。

模型始终以当前机器的 `grok models` 为准。用户指定模型、agent、推理强度或权限模式时，只影响本次调用，不修改全局配置。

## 开始前

1. 运行状态检查：

   ```powershell
   python <skill-dir>\scripts\grok_session.py status --json
   ```

2. 确认准确工作目录和任务。先阅读适用的项目指令、`git status --short`、现有差异和测试命令，保留已有修改。
3. 安装、升级、登录、修改全局 Grok/Claude 配置、提交、推送、公开分享、发布或部署，都需要用户明确授权。普通会话任务不包含这些操作。
4. 发现已有 `grok.exe` 时先读取活动会话索引、准确 PID、进程树和监听端口。不要按进程名统一终止。

## 调用 Grok

短任务和阶段任务优先使用辅助脚本。长说明写入 UTF-8 文件：

```powershell
python <skill-dir>\scripts\grok_session.py invoke `
  --dir <repo> --prompt-file <phase.txt> --json
```

脚本会调用当前 Grok CLI、保存 prompt/stdout/stderr/debug 日志、解析 JSON 回复并返回 `session_id`、实际模型、回复和日志目录。继续现有会话时使用原工作目录和准确 ID：

```powershell
python <skill-dir>\scripts\grok_session.py invoke `
  --dir <session-owner-cwd> --session-id <id> `
  --prompt-file <phase.txt> --json
```

脚本会核验 ID 与工作目录的对应关系，拒绝在其他目录继续该会话。用户明确选择模型、agent 或推理强度时，可加入 `--model`、`--agent` 或 `--reasoning-effort`。

只读分析可使用 `--permission-mode plan`。需要无人值守执行工具时，只有在用户已经授权对应目录和任务后才使用 `--always-approve`。不要为了减少提示修改用户的全局权限设置。

普通调用默认保留会话与日志。若调用超时，脚本只停止本次启动的准确进程树，并报告新会话候选与日志目录；先检查状态再决定是否继续，不要自动重复发送同一任务。

## 冒烟测试

首次配置、Grok 更新或脚本改动后运行真实测试：

```powershell
python <skill-dir>\scripts\grok_session.py smoke-test `
  --dir <safe-dir> --json
```

测试禁止工具、子 agent、规划和网页搜索，只创建一个临时会话。回复和模型验证成功后，脚本按准确 ID 删除该会话；默认生成的测试日志也会删除。若清理失败，测试应报告失败并保留可检查的记录。

## 会话发现与监督

```powershell
python <skill-dir>\scripts\grok_session.py list --dir <cwd> --json
python <skill-dir>\scripts\grok_session.py inspect --session-id <id> --json
python <skill-dir>\scripts\grok_session.py wait --session-id <id> --seconds 10 --json
```

`list` 只列出准确工作目录的会话。`inspect` 汇总状态文件、活动 PID、模型、agent、上下文、压缩次数、最新事件和待处理工具调用。`wait` 比较两次文件快照，并结合事件给出完成候选；稳定文件本身不能证明任务完成。

阶段说明应写明目标、已确认事实、允许修改的文件、禁止操作、验收命令和需要检查的页面区域。发送后确认同一会话产生新活动。

判断一轮完成需要同时确认：

- 已出现最终回复或 `turn_completed`；
- 没有待处理工具调用；
- `updates.jsonl` 与 `chat_history.jsonl` 在短时间内保持稳定；
- stdout、stderr、debug、活动进程和端口没有显示仍在工作。

Grok 的文字说明、任务清单或退出码不能单独证明完成。失败时根据真实差异编写下一阶段说明，并继续同一 ID。

## 上下文与 `/compact`

即时上下文优先读取 `signals.json` 的 `contextTokensUsed`、`contextWindowUsage` 和 `contextWindowTokens`；其次读取最新非 `turn_completed` 事件的 `_meta.totalTokens`。不要累计 debug `input_tokens`，也不要使用 `turn_completed` 的整轮累计值。

辅助脚本根据 `defaults.json` 和实际窗口返回 `effective_compact_threshold_tokens` 与 `compact_recommended`。达到提醒值后，等待当前阶段完整结束，再单独发送 `/compact`。核验时优先确认 `compactionCount` 增加，并结合 debug checkpoint、聊天记录缩短和后续上下文下降。证据不足时如实报告。

## 独立验证与安全要求

- 每阶段结束后检查准确差异，运行项目真实的构建、单元测试和受影响端到端测试；网页改动需要直接检查桌面、窄屏、关键交互、控制台和截图。
- 只处理用户授权目录。保护无关文件与已有改动，不擅自 commit、push、reset、clean、stash、删除、发布或部署。
- 若 Grok 留下 Vite、浏览器或其他服务，先确认启动时间、父子关系和端口。只停止本阶段能够确认归属的进程。
- 配置 warning 先判断是否影响当前任务。修改 `~/.grok/config.toml`、Claude 权限或代理设置前，需要用户明确要求并保存备份。
- 日志和回复不得显示认证令牌、代理凭据或敏感环境变量。

需要会话文件、超时、权限、清理和错误分类细节时读取 [references/operation-protocol.md](references/operation-protocol.md)。需要当前 CLI 参数与版本差异时读取 [references/cli-notes.md](references/cli-notes.md)。
