# Getting started

[README](../README.md) · [Command reference](./commands.md) · [Session lifecycle](./session-lifecycle.md) · [Troubleshooting](./troubleshooting.md) · [简体中文](./zh-CN/getting-started.md)

This guide follows one complete path: install the adapter, check Grok, run the compatibility test, create a session, and resume that exact session.

## Prerequisites

- Windows PowerShell;
- Python 3.10 or newer;
- an installed and authenticated Grok Build CLI;
- a working directory that Grok is authorized to read or modify.
- Codex is optional. Other coding harnesses can run the Python CLI directly.

```powershell
python --version
& "$env:USERPROFILE\.grok\bin\grok.exe" --version
& "$env:USERPROFILE\.grok\bin\grok.exe" models
```

## Install

```powershell
git clone https://github.com/ZiChenWang114514/Any-to-Grok-Build.git `
  "$env:USERPROFILE\.codex\skills\codex-grok-build"
```

The clone destination is the Codex Skill id, `codex-grok-build`. After reopening a Codex task, invoke `$codex-grok-build`. If the target directory already exists, inspect local changes with `git status --short` before updating it.

## First status check

```powershell
$skill = "$env:USERPROFILE\.codex\skills\codex-grok-build"
python "$skill\scripts\grok_session.py" status --json
```

Check that:

- `ok` is `true`;
- every `required_flag_support` value is `true`;
- `available_models` and `default_model` match the local installation;
- `doctor.ok` is `true`, or its issues are understood;
- `sessions_root_exists` is `true`;
- PID status in `active_sessions` matches the local processes.

`status` preserves network proxy variables while removing display variables and `GROK_AGENT` that can interfere with a nested doctor check.

## Compatibility smoke test

Run this after first installation, a Grok upgrade, or a helper-script change:

```powershell
python "$skill\scripts\grok_session.py" smoke-test `
  --dir "C:\path\to\safe-dir" --json
```

A successful response includes:

```json
{
  "ok": true,
  "reply": "GROK_SESSION_OK",
  "test_session_deleted": true,
  "test_logs_deleted": true
}
```

The test uses an empty tool list and disables subagents, planning, and web search. It removes only the session ID created by that run. Supplying `--log-dir` keeps the logs for inspection.

## Create the first session

Save a longer task as a UTF-8 file such as `phase-01.txt`:

```text
Inspect the repository status and project instructions. Analyze only. Report the files that may need changes and the verification commands. Do not edit files.
```

```powershell
python "$skill\scripts\grok_session.py" invoke `
  --dir "C:\path\to\repo" `
  --prompt-file "C:\path\to\phase-01.txt" `
  --permission-mode plan --json
```

Keep the returned `session_id` and `log_dir`. Normal invocations preserve both the session and the logs.

## Resume the exact session

```powershell
python "$skill\scripts\grok_session.py" invoke `
  --dir "C:\path\to\repo" `
  --session-id "<session-id>" `
  --prompt-file "C:\path\to\phase-02.txt" --json
```

The helper refuses to resume when the directory does not match the session record. This prevents a recent or similarly named session from being continued in another repository.

## Allow tool execution

When the user has authorized Grok to implement the task in the specified directory, pass `--always-approve` explicitly. It affects only that invocation. Use `--permission-mode plan` while the task is still analysis-only.

## Next steps

- [Command reference](./commands.md): all options and response fields.
- [Session lifecycle](./session-lifecycle.md): supervision and context maintenance.
- [Troubleshooting](./troubleshooting.md): startup, network, and timeout problems.
