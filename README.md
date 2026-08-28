<p align="center">
  <picture>
    <source media="(max-width: 680px)" srcset="./assets/readme/hero-mobile.svg">
    <img src="./assets/readme/hero.svg" width="100%" alt="Any-to-Grok-Build: route work from any compatible harness to exact Grok Build sessions">
  </picture>
</p>

<p align="center">
  <strong>English</strong> · <a href="./README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="./docs/getting-started.md">Quick start</a> ·
  <a href="./docs/commands.md">Command reference</a> ·
  <a href="./docs/session-lifecycle.md">Session lifecycle</a> ·
  <a href="./docs/troubleshooting.md">Troubleshooting</a> ·
  <a href="./SKILL.md">Skill instructions</a>
</p>

# Any-to-Grok-Build

Connect any compatible coding harness to local Grok Build sessions. The adapter creates, resumes, inspects, and verifies headless Grok CLI work while keeping Grok's native session files.

This repository is a local session adapter: a Python CLI, plus a Codex Skill wrapper. It does not install Grok Build, and it is not an official xAI product. The current helper has been exercised against Grok 1.0.5; runtime flags and models still follow your local `grok --help` and `grok models` output.

## What it does

- Find sessions by their exact owner directory and refuse to resume an ID in the wrong working directory.
- Create or resume a headless Grok session and keep the prompt, stdout, stderr, and debug logs.
- Read context from `signals.json` and recent events, then send `/compact` as a separate turn when needed.
- Combine `turn_completed`, pending tool calls, file stability, processes, and ports before treating a turn as finished.
- Run a real smoke test after a Grok update and delete only the test session created by that run.

Codex, Claude Code, OpenCode, and other tools can call the Python CLI. Codex users can also invoke `$codex-grok-build` after installing the Skill.

## How it works

<p align="center">
  <img src="./assets/readme/session-workflow.svg" width="100%" alt="Four-stage workflow: diagnose, invoke, observe, and verify a Grok Build session">
</p>

1. **Diagnose** — inspect the CLI, models, doctor output, session store, and active PIDs.
2. **Invoke** — create a session in an authorized directory, or resume an exact ID.
3. **Observe** — read state files, events, context, and logs before deciding the next step.
4. **Verify** — inspect the repository and run the project's own checks.

## Install

You need Python 3.10+ and an installed, authenticated Grok Build CLI.

```powershell
git clone https://github.com/ZiChenWang114514/Any-to-Grok-Build.git `
  "$env:USERPROFILE\.codex\skills\codex-grok-build"
```

The clone destination is the Codex Skill id, `codex-grok-build`. If that directory already exists, inspect local changes before updating it. Other harnesses can run `scripts/grok_session.py` directly.

## First use

### 1. Check the environment

```powershell
python "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py" `
  status --json
```

A successful result reports the Grok version, default and available models, required flags, doctor status, session store, and active sessions.

### 2. Run the compatibility smoke test

After first installation or a Grok update, create one short session in a safe directory:

```powershell
python "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py" `
  smoke-test --dir "C:\path\to\safe-dir" --json
```

The test disables tools, subagents, planning, and web search. After validating the exact reply and actual model, it removes the test session and its default temporary logs.

### 3. Create a coding session

Save a longer task as a UTF-8 text file:

```powershell
python "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py" `
  invoke --dir "C:\path\to\repo" `
  --prompt-file "C:\path\to\phase.txt" --json
```

The response includes `session_id`, actual model, reply, stop reason, and log directory. Resume with the original working directory:

```powershell
python "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py" `
  invoke --dir "C:\path\to\repo" `
  --session-id "<session-id>" `
  --prompt-file "C:\path\to\next-phase.txt" --json
```

## Commands

| Command | Purpose | Changes session state |
|---|---|:---:|
| `status` | Check installation, models, doctor, and active sessions | No |
| `list` | List sessions owned by an exact working directory | No |
| `inspect` | Inspect events, context, and PIDs for one session ID | No |
| `wait` | Compare session files and events across a short interval | No |
| `invoke` | Create or resume a headless Grok session | Yes |
| `smoke-test` | Create, validate, and remove one test session | Yes, then cleans up |

See the [command reference](./docs/commands.md) for every option and response field.

## Using it from a coding agent

```text
Use $codex-grok-build in C:\path\to\repo.
Check status, then start a session that inspects the failing tests
and reports the likely cause. Do not edit files yet.
```

Keep the request to the task, directory, and permission mode. The adapter already handles session identity, logs, and JSON output.

## Operational safety

- Normal invocations keep the Grok session and logs for later inspection.
- The helper refuses to overwrite standard invocation logs in a user-specified directory.
- On timeout, it stops only the process tree started by that invocation.
- It does not commit, push, publish, deploy, or change global Grok or Claude configuration by itself.
- `--always-approve` is added only when the caller supplies it.
- Authentication tokens and proxy credentials should never appear in prompts, repositories, or public logs.

## Documentation

| Document | Covers |
|---|---|
| [Getting started](./docs/getting-started.md) | Installation, first checks, creating and resuming sessions |
| [Command reference](./docs/commands.md) | Commands, options, responses, and exit behavior |
| [Session lifecycle](./docs/session-lifecycle.md) | Session discovery, completion checks, context, and long-running work |
| [Troubleshooting](./docs/troubleshooting.md) | Startup, networking, timeouts, warnings, processes, and logs |
| [Design notes](./docs/design.md) | Data sources, helper responsibilities, and safety design |

## Compatibility

- **Operating system** — Windows PowerShell is the primary tested environment.
- **Python** — 3.10 or newer.
- **Grok CLI** — tested with 1.0.5; model names, flags, and session files may change across versions.
- **Model selection** — the helper reads `grok models` and does not hard-code a legacy model ID.

When reporting a version difference, include `status --json`, `grok --version`, and logs after removing sensitive data.

## Machine-readable contract

Every command accepts `--json`. The shared fields are `schema_version`, `ok`, `target`, `command`, `provider`, `workdir`, `session_id`, `requested_model`, `actual_model`, `result`, `warnings`, and `error`. Adapter-specific evidence remains alongside them.

## Related adapters

| Repository | Target |
| --- | --- |
| [Any-to-OpenCode](https://github.com/ZiChenWang114514/Any-to-OpenCode) | OpenCode |
| [Any-to-Kimi-Code](https://github.com/ZiChenWang114514/Any-to-Kimi-Code) | Kimi Code |
| [Any-to-ZCode](https://github.com/ZiChenWang114514/Any-to-ZCode) | ZCode / GLM |
| [Any-to-DeepSeek-Harness](https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness) | DeepSeek Harness |
| [Any-to-Codex](https://github.com/ZiChenWang114514/Any-to-Codex) | Codex CLI |
| [Any-to-Claude-Code](https://github.com/ZiChenWang114514/Any-to-Claude-Code) | Claude Code |
| [Any-to-Pi](https://github.com/ZiChenWang114514/Any-to-Pi) | Pi |
| [Any-to-Antigravity](https://github.com/ZiChenWang114514/Any-to-Antigravity) | Google Antigravity CLI |

## License

[MIT](./LICENSE) © 2026 ZiChenWang114514
