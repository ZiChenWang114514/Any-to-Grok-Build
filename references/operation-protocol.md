# Grok Build 会话操作协议

## 会话识别

每次先确认三项：Grok session ID、创建会话时的工作目录、实际开发仓库。三者可以不同。会话目录的父目录经过 URL 编码；它能帮助判断恢复时应使用的 `--cwd`，但仍应以历史命令和状态文件交叉确认。

```powershell
& $grokExe --cwd <session-owner-cwd> sessions list -n 20
& $grokExe --cwd <session-owner-cwd> --resume <session-id> --prompt-file <file> ...
```

`grok sessions list` 在错误的当前目录可能显示空列表。不要据此认定本机没有会话。

## 发送阶段指令

阶段文件应包括：

1. 当前目标及已验证事实；
2. 需要检查的文件与数据；
3. 明确的禁止操作；
4. 验收顺序和需要检查的视觉区域；
5. 一个用于确认本阶段完成的唯一标记。

保持一项可验证任务为一个阶段。测试失败时，下一份说明只处理已经定位的失败，不要将不相关重构混入其中。

推荐 PowerShell 模板：

```powershell
& $grokExe --cwd $sessionOwnerCwd --resume $sessionId `
  --prompt-file $phaseFile --output-format plain --debug --debug-file $debugFile `
  1> $stdoutFile 2> $stderrFile
if ($LASTEXITCODE -ne 0) { throw "Grok exited with $LASTEXITCODE" }
```

先创建文本文件，再调用 `--prompt-file`。不要把长提示、JSON 或含中文的复杂内容直接拼入 `-p` 参数。

## 判断是否结束

需要同时满足：

- 出现最终回答或 `turn_completed`；
- 没有未完成的工具调用；
- `updates.jsonl` 与 `chat_history.jsonl` 在约 10 秒内保持不变；
- stdout、stderr、debug 与进程状态不显示仍在工作的迹象。

1.0.4 起可能在主回答成功、退出码为 0 后，继续报告 session title、proactive bundle 或 telemetry 的后台同步 warning。1.0.5 冒烟中 stderr 可以为空，但 `signals.json` 仍可能留下待上传 telemetry 计数。分别检查 stdout、stderr、debug 和 signals；主回答完整时，这类 warning 或待同步计数记录为非阻断问题。若模型响应本身持续重试并且没有主回答，再检查本地代理和响应流。

`grok.exe` 仍存在并不总是表示模型仍在思考。先检查子进程和端口；前端测试常留下 Vite 服务。停止服务前确认启动时间、父进程和监听端口只属于本阶段。

## 上下文维护

读取即时上下文时优先使用 `signals.json` 的 `contextTokensUsed` 或 `contextWindowUsage`，并同时记录 `contextWindowTokens`（若存在）。若它暂时没有刷新，读取最新非 `turn_completed` agent/tool 事件的 `_meta.totalTokens`。debug 中的请求 `input_tokens` 是请求计数，不能相加后当作会话上下文。

达到 250000 后，等待当前阶段完成；发送只含 `/compact` 的单独阶段；记录压缩前后的状态。后续阶段必须在压缩核验成功后才开始。

压缩核验优先看 `compactionCount`。其他证据须组合使用：debug 中的 builtin compact、持久化 checkpoint、chat history 替换或缩短、compaction 文件夹中新片段、以及后续事件上下文显著降低。

## 独立核验

先查 `git status --short` 与目标差异，区分既有改动和本阶段变化。根据项目真实脚本依次执行生产构建、单元测试和受影响端到端测试；端到端测试须覆盖桌面与手机视口时分别运行。启动预览后，直接查看截图和页面：首屏、完整页面、窄屏、关键交互状态和控制台错误都应纳入检查。

Grok 的文字说明可作为线索，不能代替结果。遇到测试绿但页面不对时，以直接观察为准；遇到页面看似正确但测试失败时，先理解断言是否在验证真实行为，再决定实现或测试调整。

## 常见情况

- CLI 缺失：报告实际路径和 `status` 结果；不要下载、登录或改代理，除非用户要求。
- 登录或网络失败：先运行 `grok doctor`、核对 Grok 自身网络设置；若使用本地代理，确认代理进程、监听地址和 Grok 的实际连接路径。
- 旧 Claude 权限规则警告：`PowerShell(...)` 前缀会被 Grok 跳过。把它改成 `Bash(...)` 后再跑 `grok inspect`，确认不再出现 unknown tool prefix。修改前备份 `~/.claude/settings.local.json`。
- 无法识别的配置键：从 `~/.grok/config.toml` 删除（1.0.5 的 `[privacy]` 已无效）。修改前备份该文件。
- `grok doctor` 报 `NO_COLOR`：先确认是否在 Grok/agent 会话内运行；用 `grok_session.py status` 或干净 PowerShell 复核，不要把父进程环境变量当成主机故障。
- `signals.json` 没有新数值：同时查看 events、updates、chat history 与 debug，报告哪类证据缺失。
- `sessions list` 为空：改用创建会话时的 `--cwd`，并检查 `%USERPROFILE%\.grok\sessions` 的实际目录。
- 1.0.5 已复核：使用 `grok --help` 重新确认参数；`--resume`、`--prompt-file`、`--output-format plain` 和 `--debug-file` 在 `grok 1.0.5 (5115b46bc9)` 已验证可用。可用新临时工作目录做一次 `--prompt-file ... --output-format json` 加 `--resume <id>` 测试，不要用现有生产会话做参数试验。
- 模型 ID：先运行 `grok models`。不要假定默认模型仍是用户指南中的 `grok-build`。
