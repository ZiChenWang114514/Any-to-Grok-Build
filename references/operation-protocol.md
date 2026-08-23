# Grok Build 操作说明

## 工作目录与会话

每次确认三项：session ID、创建会话时的工作目录、实际开发仓库。它们可能不同。Grok 会话通常保存在：

```text
%USERPROFILE%\.grok\sessions\<编码后的工作目录>\<session-id>\
```

主要文件包括：

| 文件 | 用途 |
|---|---|
| `summary.json` | 会话目录、模型、agent、标题与更新时间 |
| `signals.json` | 上下文、压缩次数、工具统计与 telemetry 状态 |
| `updates.jsonl` | 事件、工具状态、最终回复与 `turn_completed` |
| `chat_history.jsonl` | 对话、推理、工具调用与工具结果 |

恢复会话时必须使用原工作目录和准确 ID。`--continue` 与省略 ID 的 `--resume` 都可能选择当前目录最近一条记录，不适合监督脚本。

## 辅助脚本

### 状态检查

```powershell
python <skill-dir>\scripts\grok_session.py status --json
```

状态检查包括 CLI 版本、必需参数、模型列表、干净环境中的 `grok doctor`、会话目录和活动 PID。它保留代理变量，同时移除父 agent 注入的颜色变量与 `GROK_AGENT`，避免嵌套调用产生误报。

### 列出与检查会话

```powershell
python <skill-dir>\scripts\grok_session.py list --dir <cwd> --limit 20 --json
python <skill-dir>\scripts\grok_session.py inspect --session-id <id> --json
```

`list` 从本地会话目录读取准确工作目录对应的记录。`inspect` 同时读取状态文件、活动索引和最近事件，并返回：

- `session_owner_cwd` 与模型/agent；
- `pending_tool_call_ids` 与 `completion_candidate`；
- 当前上下文、实际窗口、压缩次数；
- `effective_compact_threshold_tokens` 与 `compact_recommended`；
- 活动 PID 是否仍存在。

### 创建或继续会话

```powershell
python <skill-dir>\scripts\grok_session.py invoke `
  --dir <repo> --prompt-file <phase.txt> --json

python <skill-dir>\scripts\grok_session.py invoke `
  --dir <owner-cwd> --session-id <id> `
  --prompt-file <phase.txt> --json
```

脚本通过 `--output-format json` 获取准确 `sessionId`，并为每次调用保存：

```text
prompt.txt        # 仅当使用 --prompt 或 smoke-test 时生成
stdout.log
stderr.log
debug.log
```

普通调用保留会话和日志。可用 `--log-dir` 指定日志目录。用户明确选择时可以加入：

```text
--model <id>
--agent <name-or-file>
--reasoning-effort <level>
--permission-mode <mode>
--always-approve
--max-turns <n>
--timeout <seconds>
```

`--always-approve` 允许工具无人值守执行，使用前必须确认用户已经授权该目录和任务。未获授权时保留 Grok 当前权限行为，或使用 `--permission-mode plan` 做只读分析。

### 冒烟测试

```powershell
python <skill-dir>\scripts\grok_session.py smoke-test `
  --dir <safe-dir> --json
```

测试流程：

1. 读取当前 CLI 和默认模型；
2. 创建禁止工具、子 agent、规划和网页搜索的单轮会话；
3. 验证精确回复、JSON、实际模型与会话持久化；
4. 使用本次返回的精确 ID 删除测试会话；
5. 验证会话目录已消失，并删除脚本创建的临时日志。

任何一步失败都返回非零退出码。使用 `--log-dir` 时保留日志供检查。

## 超时与中断

`invoke` 使用 `defaults.json` 的请求超时，也允许本次调用用 `--timeout` 覆盖。超时后脚本只终止自己启动的准确 PID 及其子进程，并报告：

- 进程 PID；
- 新会话候选 ID；
- stdout/stderr 尾部；
- 日志目录。

客户端超时不能单独证明模型失败。先检查候选会话、状态文件、活动 PID 与仓库差异，再决定继续、中止或发送修正说明。不要自动重发原任务，以免重复编辑。

## 阶段完成判断

阶段文件应包含目标、已确认事实、允许修改的文件、禁止操作、验收命令和视觉检查区域。每次只安排一项可验证任务。

判断完成需要组合证据：

1. 出现最终回复或 `turn_completed`；
2. `pending_tool_call_ids` 为空；
3. `updates.jsonl` 与 `chat_history.jsonl` 在短时间内保持稳定；
4. stdout、stderr 和 debug 没有显示仍在工作；
5. 活动进程、子进程和端口状态与任务一致。

`wait` 返回的 `completion_candidate=true` 只表示事件和文件稳定条件成立。仍需检查日志、进程、仓库结果与测试。

Grok 1.0.4 起可能在主回答成功后报告 session title、proactive bundle、telemetry 或 resident actor warning。主回答完整、退出码为 0、`turn_completed` 已出现时，可记录为后台问题。模型响应持续重试、回复缺失或退出码非零时，再按网络/代理故障处理。

## 上下文维护

即时值按以下顺序读取：

1. `signals.json.contextTokensUsed`；
2. `signals.json.contextWindowUsage` 与 `contextWindowTokens`；
3. 最新非 `turn_completed` agent/tool 事件的 `_meta.totalTokens`。

整轮累计 `totalTokens` 和 debug `input_tokens` 不能当作当前上下文。提醒值由 `defaults.json.compact_threshold_tokens` 给出；若实际窗口更小，辅助脚本使用窗口的 80% 作为较早提醒值并明确报告。

达到提醒值后等待当前阶段结束，再单独发送 `/compact`。核验优先确认 `compactionCount` 增加；若 signals 没有刷新，应组合检查 builtin compact、checkpoint、聊天记录替换或缩短，以及后续上下文下降。

## 配置、网络与进程

- `grok doctor` 报颜色问题：用 `status` 脚本或干净 PowerShell复核，避免父 agent 的 `NO_COLOR` 影响结果。
- `grok inspect` 报旧配置键或 Claude 权限格式：先判断是否影响当前任务。用户要求修复时，保存准确配置备份，再做范围明确的修改并复核。
- 登录或网络失败：检查 `grok models`、认证状态、本地代理进程、监听地址和 Grok 实际连接路径。不要在日志中显示令牌。
- `sessions list` 为空：检查创建会话时的工作目录，或使用辅助脚本的 `list --dir`。
- `grok.exe` 仍存在：读取 `active_sessions.json`、PID、父子进程和端口。Vite 等服务可能使会话进程保持运行；只处理能够确认属于本阶段的进程。
- 配置文件、代理规则、登录状态、正式会话和用户服务均属于用户数据。修改或删除前需要明确授权。
