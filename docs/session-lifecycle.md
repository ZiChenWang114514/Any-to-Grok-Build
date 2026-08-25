# Session lifecycle

[README](../README.md) · [Getting started](./getting-started.md) · [Command reference](./commands.md) · [Troubleshooting](./troubleshooting.md) · [简体中文](./zh-CN/session-lifecycle.md)

A Grok session can persist across multiple headless invocations. Reliable collaboration depends on three stable identifiers: session ID, the working directory used when the session was created, and the repository actually being developed.

## Session storage

```text
%USERPROFILE%\.grok\sessions\<encoded-working-directory>\<session-id>\
```

| File | Primary information |
|---|---|
| `summary.json` | Title, model, agent, message count, and timestamps |
| `signals.json` | Context, compaction count, tool statistics, and telemetry state |
| `updates.jsonl` | Events, tool states, replies, and `turn_completed` |
| `chat_history.jsonl` | Conversation, reasoning, tool calls, and tool results |

The owner directory may differ from the repository Grok actually edits. Inspect the session content and repository state before supervision; do not infer the task from the directory name alone.

## Creation stage

Before creating a session:

1. Confirm the user-authorized working directory and task.
2. Read applicable repository instructions.
3. Inspect `git status --short` and existing diffs.
4. Save longer phase instructions as UTF-8 text.
5. Choose read-only `plan` or an execution mode already authorized by the user.

A phase prompt should state the objective, confirmed facts, allowed files, prohibited actions, verification commands, and any page regions that need inspection. Assign one clearly verifiable task at a time.

## Running stage

After a successful invocation, keep the session ID, original working directory, log directory, prompt file, and invocation times. Run `inspect` before sending the next phase. Resume with the exact ID and original working directory.

## Determining whether a turn is complete

Use the following evidence together:

1. A final reply or `turn_completed` exists.
2. `pending_tool_call_ids` is empty.
3. `updates.jsonl` and `chat_history.jsonl` remain stable for a short interval.
4. stdout, stderr, and debug logs show no tools still running.
5. Active processes, child processes, and ports match the expected task state.
6. Repository diffs and verification results support Grok's completion claim.

`completion_candidate=true` and `stable=true` only narrow the inspection. Grok's prose, checklist, or exit status must still be compared with repository evidence.

## Context readings

Read current context in this order:

1. `signals.json.contextTokensUsed`;
2. `signals.json.contextWindowUsage` with `contextWindowTokens`;
3. `_meta.totalTokens` from the latest non-`turn_completed` agent or tool event.

Do not sum debug `input_tokens`, and do not treat the cumulative value on `turn_completed` as current context.

The helper reads the reminder value from `references/defaults.json`. If the actual context window is smaller, it uses 80% of that window as an earlier reminder and reports the decision.

## `/compact`

After the reminder is reached:

1. Wait for the current phase to finish completely.
2. Create a UTF-8 prompt containing only `/compact`.
3. Invoke it separately with the same session ID.
4. Inspect compaction evidence.
5. Send the next phase only after compaction is confirmed.

Prefer an increased `compactionCount`. If `signals.json` does not refresh promptly, combine debug evidence of the compact command and checkpoint with a shortened or replaced chat history and reduced context in later events.

## Long-running collaboration

```text
work/
├── phase-01-inspect.txt
├── phase-02-implement.txt
├── phase-03-fix-tests.txt
└── logs/
    ├── phase-01/
    ├── phase-02/
    └── phase-03/
```

After every turn, Codex inspects the exact diff, build, tests, and interface before writing the next phase from evidence. Do not automatically resend a timed-out task, because the same edits may run twice.

## Ending collaboration

- Stop sending new phases.
- Summarize changed files, verification results, known warnings, and decisions that still require a person.
- Inspect temporary services started during the phase.
- Stop only processes that can be attributed to the phase.
- Preserve the formal session unless the user explicitly asks to delete it.
