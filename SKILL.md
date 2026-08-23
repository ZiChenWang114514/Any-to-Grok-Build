---
name: codex-grok-build
description: 在用户要求安装、登录、检查、启动、恢复、监督、压缩或排查 Grok Build CLI 会话时使用；覆盖 Windows PowerShell、阶段指令、会话状态、上下文长度、测试、视觉核验与临时服务清理。不要用于把 Grok 注册成 Codex 原生子 Agent 或 API Provider。
---

# Codex Grok Build

将 Grok Build 作为本机外部 CLI 协作者使用。Codex 负责理解需求、生成阶段说明、独立核验结果和决定下一步；Grok 负责在明确仓库中实施。不要创建或修改 Codex 自定义 Agent TOML 来模拟 Grok Provider。

## 先做只读诊断

1. 运行状态脚本，再决定是否需要登录、恢复会话或新建会话。

   ```powershell
   python <skill-dir>\scripts\grok_session.py status --json
   ```

2. 找到 Grok 可执行文件后先运行 `--help`，以本机版本的参数为准。常见 Windows 路径为 `%USERPROFILE%\.grok\bin\grok.exe`，不可假定版本、模型或会话格式始终相同。对 1.0.4 及更新版本，额外运行 `grok doctor`、`grok inspect` 和 `grok models`；它们可能报告终端能力、旧配置 warning 或与用户指南不同的模型 ID，这些提示要与会话失败分开判断。
3. 让用户提供仓库路径、目标和会话 ID；没有这些信息时，只汇报诊断与所缺信息。不要恢复历史会话，也不要启动定时监测。
4. 先读仓库指令、`git status --short`、准确差异与已有测试命令。保留所有既有改动。

## 会话目录与恢复

Grok 通常将会话写入：

```text
%USERPROFILE%\.grok\sessions\<编码后的会话工作目录>\<session-id>\
```

该目录中的 `summary.json`、`signals.json`、`updates.jsonl` 和 `chat_history.jsonl` 是主要状态来源。使用脚本定位并检查：

```powershell
python <skill-dir>\scripts\grok_session.py inspect --session-id <id> --json
python <skill-dir>\scripts\grok_session.py wait --session-id <id> --seconds 10 --json
```

恢复时的 `--cwd` 必须是创建该会话的工作目录；它可能与实际开发仓库不同。先由会话目录的上级编码名称或历史命令确认，再运行：

```powershell
& $grokExe --cwd <session-owner-cwd> --resume <session-id> `
  --prompt-file <phase-file> --output-format plain --debug `
  --debug-file <phase-debug-log> 1> <phase-stdout-log> 2> <phase-stderr-log>
```

优先使用 `--resume <id>`。不要用可能选中错误记录的 `--continue`；也不要省略 `--resume` 的参数，1.0.5 会把它解释为恢复当前目录最近一条会话。长提示写入 UTF-8 文本文件，避免 PowerShell 引号和编码损坏；每阶段保存独立的提示、stdout、stderr 与 debug 文件。只在有明确原因时使用 `--fork-session`、`--worktree` 或 `--restore-code`。

## 阶段协作流程

1. 读会话状态、运行中 `grok.exe`、本阶段日志和仓库实时差异。
2. 将下一阶段写成简短而完整的文件：目标、已证实的问题、文件范围、禁止操作、验收命令和视觉检查点。不要把用户的内部指令原样放到产品页面。
3. 发送后确认同一会话的 `summary.json`、`updates.jsonl` 或 `chat_history.jsonl` 出现新活动。
4. 只有在最终回复或 `turn_completed` 已出现、没有未完成工具调用，并且相隔约 10 秒的两次检查均无新活动时，才判断该阶段结束。脚本的 `wait` 只证明文件是否稳定，工具调用仍需读取事件与日志确认。1.0.4 起的 headless 调用可能在主回答已经成功、退出码为 0 后，额外报告 session title、proactive bundle 或 telemetry 的后台同步 warning。1.0.5 冒烟中主回答完整时 stderr 可以为空，但 `signals.json` 仍可能显示待上传的 telemetry 队列。应分别记录 stdout、stderr、debug 和 signals，不要把这类 warning 或待同步计数单独判为阶段失败。若同时出现 `error decoding response body`、重试耗尽或主回答缺失，再按网络/代理故障处理。
5. 每阶段结束后独立审阅差异，运行构建、完整单元测试和定向端到端测试；直接检查页面与截图。Grok 的 checklist、几何数值、自述和退出码都不能单独作为完成证据。
6. 基于证据决定下一阶段或向用户报告完成。没有完成证据时，继续发送有针对性的修正说明。

## 上下文与 `/compact`

用户指定的参考阈值为 250000 tokens；先读取实际上下文窗口，再判断这个阈值是否适用。若 `signals.json` 提供 `contextWindowTokens`，应同时报告它；当实际窗口小于 250000 时，改用不高于窗口的提前提醒值，并在报告中说明依据。按如下优先级读取即时使用量：

1. `signals.json` 的 `contextTokensUsed` 或 `contextWindowUsage`；
2. 运行中最新一条非 `turn_completed` agent/tool 事件的 `_meta.totalTokens`。

忽略 `turn_completed` 的整轮累计 `totalTokens`，也不累加 debug 日志里的 `input_tokens`。若本阶段达到阈值，先等待该阶段完整结束，再单独发送只含 `/compact` 的提示文件；核验成功后才发送下一阶段。

优先确认 `compactionCount` 增加。若 `signals.json` 未更新，至少同时确认 debug 中 builtin `compact`、持久化 checkpoint、压缩后的重置或聊天记录替换、`chat_history.jsonl` 明显缩小，以及后续非 `turn_completed` 事件显示更低的上下文使用量。证据不足时如实说明，不能称压缩完成。

用户指南说明会在上下文窗口达到约 85% 时自动压缩（`[session] auto_compact_threshold_percent`）；这不能代替用户指定的提前检查，但可以作为第二条安全线。手动 `/compact` 仍需在当前阶段结束后单独发送，并按上述证据核验。

## 进程、端口与安全

- 若 Grok 结束后仍有 `grok.exe`，检查是否有本阶段启动的 Vite 或类似服务在等待。先查准确进程树和监听端口，再只停止本阶段临时服务。
- 不要按进程名批量终止，也不要影响用户已有服务。
- 不要 commit、push、发布、部署、reset、clean、stash、删除或覆盖无关文件，除非用户明确授权。
- 警告日志可能来自旧的 Claude 配置或不支持的权限规则；先确认它是否实际阻断本次命令，不要为了消除警告改动无关配置。

## 诊断脚本

`scripts/grok_session.py` 只读：

- `status`：检查 Grok CLI、`GROK_HOME`、会话目录和活动会话索引。
- `inspect --session-id`：定位会话，汇总关键文件、上下文读数、压缩计数、模型/agent 线索与最近事件。
- `wait --session-id --seconds 10`：比较两次文件快照，给出稳定性证据。
- 1.0.5 已复核：先确认 `--version`、`--resume`、`--prompt-file`、`--output-format plain` 和 `--debug-file` 仍在 `--help` 中。可在新临时工作目录中用 `--prompt-file ... --output-format json` 获取 `sessionId`，再用原阶段命令恢复该 ID，做兼容性冒烟测试，避免触碰用户现有会话。不要写死 `grok-build`：以 `grok models`、`signals.json` 的 `primaryModelId` 和 JSON 结果里的 `modelUsage` 为准。

需要命令模板、状态解释和常见故障时读取 [references/operation-protocol.md](references/operation-protocol.md)。需要具体 CLI 参数时读取 [references/cli-notes.md](references/cli-notes.md)。
