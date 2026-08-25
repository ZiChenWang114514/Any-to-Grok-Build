# Design notes

[README](../README.md) · [Getting started](./getting-started.md) · [Command reference](./commands.md) · [Session lifecycle](./session-lifecycle.md) · [简体中文](./zh-CN/design.md)

## Design goals

This skill treats Grok Build as a local external coding collaborator. The helper provides consistent commands and inspectable results; Codex interprets the task, supervises execution, and independently verifies the repository.

- Session selection is reviewable.
- Working-directory identity remains consistent.
- Invocation logs remain available for inspection.
- Timeout handling has a precise process scope.
- Context readings identify their source.
- Test sessions can be removed by exact ID.
- Normal commands do not alter global configuration or formal sessions.

## Components

| Component | Responsibility |
|---|---|
| `SKILL.md` | When Codex should use the skill and the full operating rules |
| `scripts/grok_session.py` | Diagnostics, discovery, inspection, waiting, invocation, and smoke tests |
| `references/defaults.json` | Timeouts, context reminder, and expected test reply |
| `references/operation-protocol.md` | Detailed execution guidance for the skill |
| `references/cli-notes.md` | Current Grok CLI flags and version observations |
| `evals/evals.json` | Representative requests and expected behavior |
| `docs/` | Documentation for users and maintainers |

## State sources

```text
grok --help / models / doctor
             │
             ├── installation status
             │
~/.grok/active_sessions.json
             ├── active PID and cwd
             │
~/.grok/sessions/<cwd>/<id>/
             ├── summary.json
             ├── signals.json
             ├── updates.jsonl
             └── chat_history.jsonl
```

No single source completely describes a session. A living process can mean a tool is still running or a temporary development service remains open. Likewise, `turn_completed` still needs to be compared with pending tools and repository results.

## Subcommand responsibilities

- `status`: inspect the local CLI and session infrastructure.
- `list`: find sessions from their decoded owner directory.
- `inspect`: aggregate state, events, context, and PIDs for one session.
- `wait`: compare two state-file snapshots and reread events.
- `invoke`: call Grok, parse the JSON response, and preserve logs.
- `smoke-test`: create a minimal real session, validate it, and remove the exact session.

## Process handling

The helper creates a separate process group for every `invoke`. On timeout, it handles only the process tree started by that invocation: Windows uses `taskkill /T` with the exact PID, while other systems signal the independent process group. Existing Grok, Node, browser, and development-service processes are outside automatic cleanup.

## Network and logs

Grok subprocesses inherit the current proxy configuration. The helper removes only display variables that can interfere with nested diagnostics and `GROK_AGENT`, then ensures loopback addresses appear in `NO_PROXY`. It does not change Clash, system proxy, or global Grok configuration.

Without `--log-dir`, a normal invocation creates and preserves a unique temporary directory. A successful smoke test removes its own default temporary directory. With an explicit directory, the helper preserves logs and refuses to overwrite standard log files.

## Compatibility verification

After a Grok CLI update, run:

1. `python -m py_compile scripts/grok_session.py`;
2. Skill structure validation;
3. `status --json`;
4. `smoke-test --json`;
5. one create-and-resume test using the same session;
6. exact deletion verification for the test session.
