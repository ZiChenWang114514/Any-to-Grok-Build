# 命令手册

[README](../README.md) · [快速开始](./getting-started.md) · [会话生命周期](./session-lifecycle.md) · [故障诊断](./troubleshooting.md)

以下示例假定：

```powershell
$skill = "$env:USERPROFILE\.codex\skills\codex-grok-build"
$helper = "$skill\scripts\grok_session.py"
```

所有子命令都支持 `--json`。成功时通常以状态 `0` 结束；诊断失败、输入错误、Grok 调用失败或清理失败时，进程以非零状态结束。

## `status`

检查 Grok 可执行文件、版本、关键参数、模型、doctor、会话目录和活动会话。

```powershell
python $helper status --json
python $helper status --grok "C:\custom\grok.exe" --json
```

## `list`

```powershell
python $helper list --dir "C:\path\to\repo" --limit 20 --json
```

`--dir` 是创建会话时使用的工作目录；`--limit` 范围为 1–500，默认 20。

## `inspect`

```powershell
python $helper inspect --session-id "<session-id>" --json
```

重要字段包括：

- `session_owner_cwd`：会话所属工作目录；
- `summary_current_model_id`、`summary_agent_name`：会话摘要中的模型和 Agent；
- `activity.pending_tool_call_ids`：尚未结束的工具调用；
- `activity.completion_candidate`：根据事件形成的完成候选；
- `signals_contextTokensUsed` 与 `signals_contextWindowTokens`；
- `compact_recommended` 与 `signals_compactionCount`；
- `active_registry_entries`：活动索引中的 PID 与存活状态。

## `wait`

```powershell
python $helper wait --session-id "<session-id>" --seconds 10 --json
```

`stable=true` 仅表示检查期间目标文件没有变化。还需要确认没有待处理工具调用，并检查日志、进程和仓库结果。

## `invoke`

```powershell
python $helper invoke `
  --dir "C:\path\to\repo" `
  --prompt-file "C:\path\to\phase.txt" --json
```

继续会话时增加 `--session-id "<session-id>"`。`--prompt` 与 `--prompt-file` 二选一，较长任务优先使用 UTF-8 文件。

### 调用参数

| 参数 | 说明 |
|---|---|
| `--dir` | 会话工作目录，必填 |
| `--session-id` | 继续已有会话时使用的准确 ID |
| `--prompt` / `--prompt-file` | 直接提示或 UTF-8 提示文件 |
| `--grok` | 指定 Grok 可执行文件 |
| `--model` | 本次调用使用的模型 ID |
| `--agent` | Agent 名称或文件 |
| `--reasoning-effort` | 本次调用的推理强度 |
| `--permission-mode` | Grok 权限模式 |
| `--always-approve` | 自动批准本次调用中的工具执行 |
| `--max-turns` | 限制无头调用轮数 |
| `--timeout` | 本次调用超时秒数 |
| `--log-dir` | 保存调用日志的目录 |

`--always-approve` 与 `--permission-mode` 同时出现时，辅助脚本优先传入 `--always-approve`。指定目录已经包含 `stdout.log`、`stderr.log` 或 `debug.log` 时，脚本会停止并报告冲突。

成功输出包含 `session_id`、`created_session`、`actual_models`、`reply`、`stop_reason` 和 `log_dir`。显示模型、JSON 中的实际模型和会话 Agent 名称可能不同，应分别记录。

## `smoke-test`

```powershell
python $helper smoke-test --dir "C:\path\to\safe-dir" --json
```

它会创建一次单轮会话，验证固定回复和实际模型，再使用准确 ID 删除该会话。可使用 `--model`、`--reasoning-effort`、`--timeout`、`--grok` 或 `--log-dir` 检查特定配置。

## 默认参数

请求超时、测试超时、上下文提醒值和固定测试回复保存在 [`references/defaults.json`](../references/defaults.json)。修改后应重新运行 Python 编译检查、Skill 校验和真实冒烟测试。
