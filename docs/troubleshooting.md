# Troubleshooting

[README](../README.md) · [Getting started](./getting-started.md) · [Command reference](./commands.md) · [Session lifecycle](./session-lifecycle.md) · [简体中文](./zh-CN/troubleshooting.md)

Start with the unified status check:

```powershell
$helper = "$env:USERPROFILE\.codex\skills\codex-grok-build\scripts\grok_session.py"
python $helper status --json
```

## Grok startup timeout

Typical symptoms include `startup timed out` or a long pause while loading account settings. Check:

1. Whether `grok --version` returns promptly.
2. Whether `grok models` can read the account and model catalog.
3. Whether `grok doctor` reports authentication or network problems.
4. `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and `NO_PROXY` in PowerShell.
5. The local proxy process and its listening port.
6. Whether Grok traffic follows the expected route.

The helper preserves proxy variables and adds `127.0.0.1`, `localhost`, and `::1` to `NO_PROXY`. Never display proxy passwords or authentication tokens in diagnostic output.

## Doctor reports a color issue

A parent agent may inject `NO_COLOR` or related display variables and cause a false warning in nested `grok doctor` runs. Prefer the helper's doctor result or rerun doctor from a clean PowerShell process.

## Session not found

Common causes include a different original working directory, an incorrect session ID, a deleted session, or `GROK_HOME` pointing elsewhere.

```powershell
python $helper list --dir "C:\original\cwd" --json
```

Do not guess with `--resume` when no ID is supplied.

## Working directory mismatch

`invoke --session-id` verifies the session owner directory. On mismatch, read `session_owner_cwd` from `inspect`, confirm the directory still exists, and inspect the actual task stored in the session.

## Invocation timeout

After timeout, the helper stops the process tree started by that invocation and returns the starting PID, candidate session IDs, stdout/stderr tails, and log directory in the error JSON.

Inspect candidate sessions, repository changes, and logs before retrying. The model may already have made partial edits, so automatically resending the same prompt can duplicate work.

## Main reply succeeded but stderr has warnings

Grok 1.0.4–1.0.5 may report session title generation, proactive bundle, telemetry, plugin collision, or resident session actor warnings after the main response.

When the JSON reply is complete, exit status is 0, `turn_completed` exists, and tool calls have ended, record these as background warnings. If the model reply is absent, retries continue, or the exit status is non-zero, inspect the network, proxy, and upstream response.

## `error decoding response body`

- The main task may still have succeeded when the error affects only title generation or background synchronization.
- When it interrupts the main model response and exhausts retries, inspect the network route.
- Compare stdout, stderr, debug, and session events instead of judging from one log line.

## `grok.exe` remains active

The session may have started Vite, a browser, or another long-running service. Inspect the exact PID in the active registry, parent-child relationships, listening ports, start time, and service origin.

Stop only processes that can be attributed to the phase. Do not terminate every `grok.exe`, Node, or browser process by name.

## Log inspection

Every `invoke` writes `stdout.log`, `stderr.log`, and `debug.log`; `--prompt` and `smoke-test` also write `prompt.txt`.

Before sharing an issue publicly, remove usernames, absolute paths, session and request IDs, authentication tokens, proxy credentials, private repository details, and unpublished prompts.

## Global configuration warnings

`grok inspect` may report obsolete keys or Claude permission formats. First determine whether the warning affects the current invocation. Obtain explicit user authorization and save an identifiable backup before changing `~/.grok/config.toml`, Claude permissions, or proxy configuration.
