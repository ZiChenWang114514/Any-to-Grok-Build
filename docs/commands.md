# Command reference

[README](../README.md) · [Getting started](./getting-started.md) · [Session lifecycle](./session-lifecycle.md) · [Troubleshooting](./troubleshooting.md) · [简体中文](./zh-CN/commands.md)

The examples assume:

```powershell
$skill = "$env:USERPROFILE\.codex\skills\codex-grok-build"
$helper = "$skill\scripts\grok_session.py"
```

Every subcommand supports `--json`. Successful commands normally exit with status `0`; invalid input, failed diagnostics, Grok invocation errors, and cleanup failures return a non-zero status.

## `status`

Checks the Grok executable, version, required flags, models, doctor result, session store, and active sessions.

```powershell
python $helper status --json
python $helper status --grok "C:\custom\grok.exe" --json
```

## `list`

```powershell
python $helper list --dir "C:\path\to\repo" --limit 20 --json
```

`--dir` is the working directory used to create the session. `--limit` accepts 1–500 and defaults to 20.

## `inspect`

```powershell
python $helper inspect --session-id "<session-id>" --json
```

Important fields include:

- `session_owner_cwd`: owner directory recorded for the session;
- `summary_current_model_id` and `summary_agent_name`: model and agent from the summary;
- `activity.pending_tool_call_ids`: tool calls without a terminal state;
- `activity.completion_candidate`: event-based completion candidate;
- `signals_contextTokensUsed` and `signals_contextWindowTokens`;
- `compact_recommended` and `signals_compactionCount`;
- `active_registry_entries`: active PIDs and liveness information.

## `wait`

```powershell
python $helper wait --session-id "<session-id>" --seconds 10 --json
```

`stable=true` only means the target files did not change during the interval. You must still check pending tools, logs, processes, and repository results.

## `invoke`

```powershell
python $helper invoke `
  --dir "C:\path\to\repo" `
  --prompt-file "C:\path\to\phase.txt" --json
```

Add `--session-id "<session-id>"` to resume a session. Choose either `--prompt` or `--prompt-file`; use a UTF-8 file for longer tasks.

### Invocation options

| Option | Description |
|---|---|
| `--dir` | Session working directory; required |
| `--session-id` | Exact ID when resuming a session |
| `--prompt` / `--prompt-file` | Direct prompt or UTF-8 prompt file |
| `--grok` | Grok executable path |
| `--model` | Model ID for this invocation |
| `--agent` | Agent name or file |
| `--reasoning-effort` | Reasoning effort for this invocation |
| `--permission-mode` | Grok permission mode |
| `--always-approve` | Approve tool execution for this invocation |
| `--max-turns` | Limit headless turns |
| `--timeout` | Timeout in seconds |
| `--log-dir` | Invocation log directory |

When both are supplied, `--always-approve` takes precedence over `--permission-mode`. If the selected directory already contains `stdout.log`, `stderr.log`, or `debug.log`, the helper stops and reports the conflict.

Successful output includes `session_id`, `created_session`, `actual_models`, `reply`, `stop_reason`, and `log_dir`. The displayed model, model reported by JSON usage, and session agent name may differ; record each source separately.

## `smoke-test`

```powershell
python $helper smoke-test --dir "C:\path\to\safe-dir" --json
```

This creates one single-turn session, validates the fixed reply and actual model, then deletes the exact ID. Use `--model`, `--reasoning-effort`, `--timeout`, `--grok`, or `--log-dir` to check a specific configuration.

## Defaults

Request timeout, smoke-test timeout, context reminder, and expected reply live in [`references/defaults.json`](../references/defaults.json). After changing them, rerun Python compilation, Skill validation, and a real smoke test.
