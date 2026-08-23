#!/usr/bin/env python3
"""Diagnose, invoke, resume, and smoke-test local Grok Build sessions."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable
from urllib.parse import unquote


SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = SKILL_DIR / "references" / "defaults.json"
KNOWN_FILES = ("summary.json", "signals.json", "updates.jsonl", "chat_history.jsonl")
DEFAULT_GROK = Path.home() / ".grok" / "bin" / "grok.exe"
REQUIRED_FLAGS = (
    "--cwd",
    "--resume",
    "--prompt-file",
    "--output-format",
    "--debug-file",
)
COLOR_ENV_KEYS = {
    "NO_COLOR",
    "FORCE_COLOR",
    "CLICOLOR",
    "CLICOLOR_FORCE",
    "PIP_NO_COLOR",
    "CARGO_TERM_COLOR",
    "NPM_CONFIG_COLOR",
}
TERMINAL_TOOL_STATES = {
    "completed",
    "failed",
    "cancelled",
    "canceled",
    "done",
    "success",
    "error",
}
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def load_defaults() -> dict[str, Any]:
    with DEFAULTS_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    for name in ("request_timeout_seconds", "smoke_timeout_seconds", "compact_threshold_tokens"):
        if not isinstance(data.get(name), int) or data[name] <= 0:
            raise ValueError(f"Invalid {name} in {DEFAULTS_PATH}")
    if not isinstance(data.get("smoke_reply"), str) or not data["smoke_reply"].strip():
        raise ValueError(f"Invalid smoke_reply in {DEFAULTS_PATH}")
    return data


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def grok_home() -> Path:
    return Path(os.environ.get("GROK_HOME", Path.home() / ".grok")).expanduser()


def grok_subprocess_env() -> dict[str, str]:
    """Remove parent-agent display settings while preserving network variables."""
    environment = os.environ.copy()
    for key in list(environment):
        upper = key.upper()
        if upper in COLOR_ENV_KEYS or upper.endswith("_COLOR") or upper == "GROK_AGENT":
            environment.pop(key, None)
    raw_no_proxy = environment.get("NO_PROXY", environment.get("no_proxy", ""))
    entries = [item.strip() for item in raw_no_proxy.split(",") if item.strip()]
    for item in ("127.0.0.1", "localhost", "::1"):
        if item not in entries:
            entries.append(item)
    environment["NO_PROXY"] = environment["no_proxy"] = ",".join(entries)
    return environment


def locate_executable(explicit: str | None) -> Path | None:
    choices = [explicit, os.environ.get("GROK_EXE"), str(DEFAULT_GROK), shutil.which("grok")]
    for item in choices:
        if item:
            path = Path(item).expanduser()
            if path.is_file():
                return path.resolve()
    return None


def run_cli(
    executable: Path,
    *arguments: str,
    timeout: int = 30,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(executable), *arguments],
        cwd=str(cwd) if cwd else None,
        env=grok_subprocess_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def clean_output(text: str) -> str:
    return ANSI_RE.sub("", text).strip()


def read_tail(path: Path, maximum_chars: int = 6000) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[-maximum_chars:]


def json_file(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def tail_lines(path: Path, maximum_bytes: int = 2_500_000) -> list[str]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - maximum_bytes))
            raw = handle.read()
    except OSError:
        return []
    return raw.decode("utf-8", errors="replace").splitlines()


def values_named(value: Any, names: set[str]) -> Iterable[Any]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in names:
                yield child
            yield from values_named(child, names)
    elif isinstance(value, list):
        for child in value:
            yield from values_named(child, names)


def normalized_path(path: Path) -> str:
    resolved = str(path.expanduser().resolve())
    return os.path.normcase(os.path.normpath(resolved))


def decoded_owner(session_dir: Path) -> str:
    return unquote(session_dir.parent.name)


def find_session(session_id: str, home: Path) -> list[Path]:
    root = home / "sessions"
    if not root.is_dir():
        return []
    return sorted(path for path in root.glob(f"*/{session_id}") if path.is_dir())


def owner_directories(home: Path, workdir: Path) -> list[Path]:
    root = home / "sessions"
    if not root.is_dir():
        return []
    expected = normalized_path(workdir)
    matches: list[Path] = []
    for candidate in root.iterdir():
        if not candidate.is_dir():
            continue
        try:
            decoded = Path(unquote(candidate.name))
            if normalized_path(decoded) == expected:
                matches.append(candidate)
        except (OSError, RuntimeError):
            continue
    return matches


def session_ids_for_workdir(home: Path, workdir: Path) -> set[str]:
    result: set[str] = set()
    for owner in owner_directories(home, workdir):
        result.update(child.name for child in owner.iterdir() if child.is_dir())
    return result


def file_snapshot(session_dir: Path) -> dict[str, dict[str, int] | None]:
    result: dict[str, dict[str, int] | None] = {}
    for name in KNOWN_FILES:
        path = session_dir / name
        if path.is_file():
            stat = path.stat()
            result[name] = {"bytes": stat.st_size, "modified_ns": stat.st_mtime_ns}
        else:
            result[name] = None
    return result


def latest_non_completed_total_tokens(paths: Iterable[Path]) -> int | None:
    latest: int | None = None
    for path in paths:
        for line in tail_lines(path):
            if "turn_completed" in line.lower():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            numbers = [value for value in values_named(item, {"totalTokens"}) if isinstance(value, int)]
            if numbers:
                latest = numbers[-1]
    return latest


def recent_markers(paths: Iterable[Path]) -> list[str]:
    markers: list[str] = []
    for path in paths:
        tail = "\n".join(tail_lines(path)[-250:]).lower()
        for marker in ("turn_completed", "toolcall", "tool_call", "final"):
            if marker in tail and marker not in markers:
                markers.append(marker)
    return markers


def session_activity(session_dir: Path) -> dict[str, Any]:
    updates_path = session_dir / "updates.jsonl"
    tool_states: dict[str, str] = {}
    last_update_type: str | None = None
    last_prompt_id: str | None = None
    last_event_id: str | None = None
    turn_completed_count = 0
    last_turn_stop_reason: str | None = None
    for line in tail_lines(updates_path):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        params = item.get("params") if isinstance(item, dict) else None
        params = params if isinstance(params, dict) else {}
        update = params.get("update")
        update = update if isinstance(update, dict) else {}
        meta = params.get("_meta")
        meta = meta if isinstance(meta, dict) else {}
        update_type = update.get("sessionUpdate")
        if isinstance(update_type, str):
            last_update_type = update_type
        prompt_id = update.get("prompt_id") or update.get("promptId") or meta.get("promptId")
        if isinstance(prompt_id, str):
            last_prompt_id = prompt_id
        event_id = meta.get("eventId")
        if isinstance(event_id, str):
            last_event_id = event_id
        if update_type == "turn_completed":
            turn_completed_count += 1
            stop_reason = update.get("stop_reason") or update.get("stopReason")
            if isinstance(stop_reason, str):
                last_turn_stop_reason = stop_reason
        if update_type in {"tool_call", "tool_call_update"}:
            tool_id = update.get("toolCallId") or update.get("tool_call_id") or update.get("id")
            status = update.get("status")
            if not isinstance(status, str):
                status_values = [value for value in values_named(update, {"status"}) if isinstance(value, str)]
                status = status_values[-1] if status_values else "pending"
            if isinstance(tool_id, str):
                tool_states[tool_id] = status.lower()
    pending = sorted(
        tool_id for tool_id, state in tool_states.items()
        if state not in TERMINAL_TOOL_STATES
    )
    return {
        "last_update_type": last_update_type,
        "last_prompt_id": last_prompt_id,
        "last_event_id": last_event_id,
        "turn_completed_count_in_tail": turn_completed_count,
        "last_turn_stop_reason": last_turn_stop_reason,
        "pending_tool_call_ids": pending,
        "completion_candidate": bool(turn_completed_count and not pending),
    }


def process_alive(pid: Any) -> bool | None:
    if not isinstance(pid, int) or pid <= 0:
        return None
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        error = ctypes.windll.kernel32.GetLastError()
        return False if error == 87 else None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return None


def active_session_entries(home: Path) -> list[dict[str, Any]]:
    raw = json_file(home / "active_sessions.json")
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        pid = item.get("pid")
        result.append(
            {
                "session_id": item.get("session_id"),
                "pid": pid,
                "pid_alive": process_alive(pid),
                "cwd": item.get("cwd"),
                "opened_at": item.get("opened_at"),
            }
        )
    return result


def run_grok_doctor(executable: Path) -> dict[str, Any]:
    try:
        completed = run_cli(executable, "doctor", timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc), "issues": [], "issue_count": None}
    output = clean_output(completed.stdout or "")
    issues = [line.strip() for line in output.splitlines() if line.lstrip().startswith("!")]
    return {
        "ok": completed.returncode == 0 and not issues,
        "exit_code": completed.returncode,
        "issues": issues,
        "issue_count": len(issues),
        "parent_had_no_color": bool(os.environ.get("NO_COLOR")),
    }


def status_payload(args: argparse.Namespace) -> dict[str, Any]:
    home = grok_home()
    executable = locate_executable(args.grok)
    if not executable:
        return {
            "ok": False,
            "status": "grok_executable_missing",
            "grok_home": str(home),
            "grok_executable": None,
        }
    version = run_cli(executable, "--version", timeout=10)
    help_result = run_cli(executable, "--help", timeout=15)
    models = run_cli(executable, "models", timeout=60)
    help_text = clean_output(help_result.stdout or help_result.stderr)
    models_text = clean_output(models.stdout or models.stderr)
    default_match = re.search(r"^Default model:\s*(.+)$", models_text, flags=re.MULTILINE)
    available_models = []
    for line in models_text.splitlines():
        match = re.match(r"^\s*(?:\*|-)\s+([^\s(]+)", line)
        if match:
            available_models.append(match.group(1))
    flag_support = {flag: flag in help_text for flag in REQUIRED_FLAGS}
    active = active_session_entries(home)
    doctor = run_grok_doctor(executable)
    ok = (
        version.returncode == 0
        and help_result.returncode == 0
        and models.returncode == 0
        and all(flag_support.values())
        and doctor.get("ok") is True
    )
    return {
        "ok": ok,
        "status": "ready" if ok else "attention_required",
        "grok_home": str(home),
        "grok_executable": str(executable),
        "version": clean_output(version.stdout or version.stderr),
        "required_flag_support": flag_support,
        "models_exit_code": models.returncode,
        "default_model": default_match.group(1).strip() if default_match else None,
        "available_models": available_models,
        "doctor": doctor,
        "sessions_root": str(home / "sessions"),
        "sessions_root_exists": (home / "sessions").is_dir(),
        "active_sessions": active,
        "active_sessions_index_count": len(active),
    }


def session_summary(session_dir: Path) -> dict[str, Any]:
    summary = json_file(session_dir / "summary.json")
    summary = summary if isinstance(summary, dict) else {}
    return {
        "session_id": session_dir.name,
        "owner_cwd": decoded_owner(session_dir),
        "created_at": summary.get("created_at"),
        "updated_at": summary.get("updated_at"),
        "summary": summary.get("session_summary"),
        "current_model_id": summary.get("current_model_id"),
        "agent_name": summary.get("agent_name"),
        "num_messages": summary.get("num_messages"),
    }


def list_payload(args: argparse.Namespace) -> dict[str, Any]:
    workdir = Path(args.dir).expanduser().resolve()
    if not workdir.is_dir():
        raise NotADirectoryError(f"Work directory does not exist: {workdir}")
    sessions: list[dict[str, Any]] = []
    for owner in owner_directories(grok_home(), workdir):
        sessions.extend(session_summary(path) for path in owner.iterdir() if path.is_dir())
    sessions.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return {
        "ok": True,
        "workdir": str(workdir),
        "count": min(len(sessions), args.limit),
        "sessions": sessions[: args.limit],
    }


def inspect_payload(args: argparse.Namespace) -> dict[str, Any]:
    home = grok_home()
    matches = find_session(args.session_id, home)
    if len(matches) != 1:
        return {
            "ok": False,
            "status": "session_not_found" if not matches else "session_ambiguous",
            "session_id": args.session_id,
            "matches": [str(path) for path in matches],
            "sessions_root": str(home / "sessions"),
        }
    session_dir = matches[0]
    signals = json_file(session_dir / "signals.json")
    summary = json_file(session_dir / "summary.json")
    context_tokens = list(values_named(signals, {"contextTokensUsed"})) if signals is not None else []
    context_usage = list(values_named(signals, {"contextWindowUsage"})) if signals is not None else []
    context_window_tokens = list(values_named(signals, {"contextWindowTokens"})) if signals is not None else []
    compactions = list(values_named(signals, {"compactionCount"})) if signals is not None else []
    primary_models = list(values_named(signals, {"primaryModelId"})) if signals is not None else []
    summary_model = summary.get("current_model_id") if isinstance(summary, dict) else None
    summary_agent = summary.get("agent_name") if isinstance(summary, dict) else None
    event_paths = [session_dir / "updates.jsonl", session_dir / "chat_history.jsonl"]
    defaults = load_defaults()
    used = context_tokens[-1] if context_tokens else latest_non_completed_total_tokens(event_paths)
    window = context_window_tokens[-1] if context_window_tokens else None
    configured_threshold = defaults["compact_threshold_tokens"]
    effective_threshold = configured_threshold
    if isinstance(window, int) and window < configured_threshold:
        effective_threshold = max(1, int(window * 0.8))
    active = [item for item in active_session_entries(home) if item.get("session_id") == args.session_id]
    return {
        "ok": True,
        "status": "found",
        "session_id": args.session_id,
        "session_dir": str(session_dir),
        "session_owner_encoded": session_dir.parent.name,
        "session_owner_cwd": decoded_owner(session_dir),
        "files": file_snapshot(session_dir),
        "active_registry_entries": active,
        "signals_contextTokensUsed": context_tokens[-1] if context_tokens else None,
        "signals_contextWindowUsage": context_usage[-1] if context_usage else None,
        "signals_contextWindowTokens": window,
        "signals_compactionCount": compactions[-1] if compactions else None,
        "signals_primaryModelId": primary_models[-1] if primary_models else None,
        "summary_current_model_id": summary_model if isinstance(summary_model, str) else None,
        "summary_agent_name": summary_agent if isinstance(summary_agent, str) else None,
        "latest_non_turn_completed_totalTokens": latest_non_completed_total_tokens(event_paths),
        "recent_event_markers": recent_markers(event_paths),
        "activity": session_activity(session_dir),
        "configured_compact_threshold_tokens": configured_threshold,
        "effective_compact_threshold_tokens": effective_threshold,
        "compact_recommended": isinstance(used, int) and used >= effective_threshold,
        "summary_available": summary is not None,
    }


def wait_payload(args: argparse.Namespace) -> dict[str, Any]:
    if not 1 <= args.seconds <= 60:
        raise ValueError("--seconds must be between 1 and 60")
    matches = find_session(args.session_id, grok_home())
    if len(matches) != 1:
        return inspect_payload(args)
    session_dir = matches[0]
    before = file_snapshot(session_dir)
    time.sleep(args.seconds)
    after = file_snapshot(session_dir)
    activity = session_activity(session_dir)
    return {
        "ok": True,
        "status": "stable" if before == after else "changed",
        "session_id": args.session_id,
        "seconds": args.seconds,
        "before": before,
        "after": after,
        "activity": activity,
        "completion_candidate": before == after and activity.get("completion_candidate") is True,
        "note": "File stability alone does not prove that a Grok turn has finished.",
    }


def stop_owned_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, 15)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def parse_json_output(text: str) -> dict[str, Any]:
    cleaned = clean_output(text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    for line in reversed(cleaned.splitlines()):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Grok stdout did not contain a JSON object")


def validate_resume_owner(session_id: str, workdir: Path) -> Path:
    matches = find_session(session_id, grok_home())
    if len(matches) != 1:
        state = "not found" if not matches else "ambiguous"
        raise ValueError(f"Session {session_id} is {state}")
    owner = Path(decoded_owner(matches[0]))
    if normalized_path(owner) != normalized_path(workdir):
        raise ValueError(f"Session {session_id} belongs to {owner}, not {workdir}")
    return matches[0]


def invoke_payload(args: argparse.Namespace, smoke_test: bool = False) -> dict[str, Any]:
    defaults = load_defaults()
    executable = locate_executable(args.grok)
    if not executable:
        raise FileNotFoundError("Grok CLI was not found")
    workdir = Path(args.dir).expanduser().resolve()
    if not workdir.is_dir():
        raise NotADirectoryError(f"Work directory does not exist: {workdir}")
    session_id = getattr(args, "session_id", None)
    if session_id:
        validate_resume_owner(session_id, workdir)
    before_ids = session_ids_for_workdir(grok_home(), workdir)
    timeout = int(args.timeout or (
        defaults["smoke_timeout_seconds"] if smoke_test else defaults["request_timeout_seconds"]
    ))
    log_dir = (
        Path(args.log_dir).expanduser().resolve()
        if getattr(args, "log_dir", None)
        else Path(tempfile.mkdtemp(prefix="codex-grok-"))
    )
    if getattr(args, "log_dir", None) and log_dir.exists():
        existing_logs = [
            path.name
            for path in (log_dir / "stdout.log", log_dir / "stderr.log", log_dir / "debug.log")
            if path.exists()
        ]
        if existing_logs:
            raise FileExistsError(
                f"Log directory already contains invocation logs: {log_dir} ({', '.join(existing_logs)})"
            )
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    debug_path = log_dir / "debug.log"
    if smoke_test:
        prompt = f"Reply with exactly {defaults['smoke_reply']}. Do not use tools."
        prompt_path = log_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
    elif getattr(args, "prompt_file", None):
        prompt_path = Path(args.prompt_file).expanduser().resolve()
        if not prompt_path.is_file():
            raise FileNotFoundError(f"Prompt file does not exist: {prompt_path}")
        if not prompt_path.read_text(encoding="utf-8-sig").strip():
            raise ValueError("Prompt file is empty")
    else:
        prompt = getattr(args, "prompt", None)
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("A non-empty --prompt or --prompt-file is required")
        prompt_path = log_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
    command = [str(executable), "--cwd", str(workdir)]
    if session_id:
        command.extend(["--resume", session_id])
    if getattr(args, "model", None):
        command.extend(["--model", args.model])
    if getattr(args, "agent", None):
        command.extend(["--agent", args.agent])
    if getattr(args, "reasoning_effort", None):
        command.extend(["--reasoning-effort", args.reasoning_effort])
    if getattr(args, "always_approve", False):
        command.append("--always-approve")
    elif getattr(args, "permission_mode", None):
        command.extend(["--permission-mode", args.permission_mode])
    max_turns = 1 if smoke_test else getattr(args, "max_turns", None)
    if max_turns:
        command.extend(["--max-turns", str(max_turns)])
    if smoke_test:
        command.extend([
            "--tools",
            "",
            "--no-subagents",
            "--no-plan",
            "--disable-web-search",
        ])
    command.extend([
        "--prompt-file",
        str(prompt_path),
        "--output-format",
        "json",
        "--debug",
        "--debug-file",
        str(debug_path),
    ])
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=str(workdir),
            env=grok_subprocess_env(),
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
        )
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            stop_owned_process(process)
            after_ids = session_ids_for_workdir(grok_home(), workdir)
            raise TimeoutError(json.dumps({
                "message": f"Grok did not finish within {timeout}s",
                "pid": process.pid,
                "new_session_candidates": sorted(after_ids - before_ids),
                "log_dir": str(log_dir),
                "stdout_tail": read_tail(stdout_path),
                "stderr_tail": read_tail(stderr_path),
            }, ensure_ascii=False)) from exc
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    if exit_code != 0:
        after_ids = session_ids_for_workdir(grok_home(), workdir)
        raise RuntimeError(json.dumps({
            "message": f"Grok exited with code {exit_code}",
            "new_session_candidates": sorted(after_ids - before_ids),
            "log_dir": str(log_dir),
            "stdout_tail": stdout_text[-6000:],
            "stderr_tail": stderr_text[-6000:],
        }, ensure_ascii=False))
    result = parse_json_output(stdout_text)
    actual_session_id = result.get("sessionId")
    if not isinstance(actual_session_id, str) or not actual_session_id:
        raise RuntimeError(f"Grok JSON omitted sessionId; logs: {log_dir}")
    if session_id and actual_session_id != session_id:
        raise RuntimeError(f"Requested session {session_id}, received {actual_session_id}")
    reply = result.get("text")
    if not isinstance(reply, str) or not reply.strip():
        raise RuntimeError(f"Grok JSON omitted a non-empty text response; logs: {log_dir}")
    created_session = session_id is None
    if created_session and actual_session_id in before_ids:
        raise RuntimeError(f"Grok reused pre-existing session {actual_session_id}")
    session_matches = find_session(actual_session_id, grok_home())
    model_usage = result.get("modelUsage")
    actual_models = sorted(model_usage) if isinstance(model_usage, dict) else []
    payload = {
        "ok": True,
        "session_id": actual_session_id,
        "created_session": created_session,
        "workdir": str(workdir),
        "requested_model": getattr(args, "model", None),
        "actual_models": actual_models,
        "agent": getattr(args, "agent", None),
        "reply": reply,
        "stop_reason": result.get("stopReason"),
        "request_id": result.get("requestId"),
        "log_dir": str(log_dir),
        "debug_file": str(debug_path),
        "session_persisted": len(session_matches) == 1,
        "stderr_tail": clean_output(stderr_text[-2000:]) if stderr_text.strip() else "",
    }
    if smoke_test:
        expected = defaults["smoke_reply"]
        if reply.strip() != expected:
            raise RuntimeError(f"Unexpected smoke-test reply {reply!r}; logs: {log_dir}")
        delete_result = run_cli(
            executable,
            "--cwd",
            str(workdir),
            "sessions",
            "delete",
            actual_session_id,
            timeout=30,
            cwd=workdir,
        )
        deleted = delete_result.returncode == 0 and not find_session(actual_session_id, grok_home())
        payload["test_session_deleted"] = deleted
        payload["delete_exit_code"] = delete_result.returncode
        if not deleted:
            raise RuntimeError(
                f"Smoke test passed but exact session cleanup failed for {actual_session_id}; logs: {log_dir}"
            )
        if not getattr(args, "log_dir", None):
            shutil.rmtree(log_dir, ignore_errors=True)
            payload["log_dir"] = None
            payload["debug_file"] = None
            payload["test_logs_deleted"] = True
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Read-only installation diagnostics")
    status_parser.add_argument("--grok")
    status_parser.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list", help="List sessions for an exact work directory")
    list_parser.add_argument("--dir", required=True)
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--json", action="store_true")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect an exact session ID")
    inspect_parser.add_argument("--session-id", required=True)
    inspect_parser.add_argument("--json", action="store_true")

    wait_parser = subparsers.add_parser("wait", help="Compare session files across a short interval")
    wait_parser.add_argument("--session-id", required=True)
    wait_parser.add_argument("--seconds", type=int, default=10)
    wait_parser.add_argument("--json", action="store_true")

    for name, help_text in (
        ("invoke", "Create or continue a controlled Grok session"),
        ("smoke-test", "Run and delete a temporary compatibility session"),
    ):
        command_parser = subparsers.add_parser(name, help=help_text)
        command_parser.add_argument("--dir", required=True)
        command_parser.add_argument("--grok")
        command_parser.add_argument("--model")
        command_parser.add_argument("--agent")
        command_parser.add_argument("--reasoning-effort")
        command_parser.add_argument(
            "--permission-mode",
            choices=("default", "acceptEdits", "auto", "dontAsk", "bypassPermissions", "plan"),
        )
        command_parser.add_argument("--always-approve", action="store_true")
        command_parser.add_argument("--max-turns", type=int)
        command_parser.add_argument("--timeout", type=int)
        command_parser.add_argument("--log-dir")
        command_parser.add_argument("--json", action="store_true")
        if name == "invoke":
            prompt_group = command_parser.add_mutually_exclusive_group(required=True)
            prompt_group.add_argument("--prompt")
            prompt_group.add_argument("--prompt-file")
            command_parser.add_argument("--session-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "status":
            result = status_payload(args)
        elif args.command == "list":
            if not 1 <= args.limit <= 500:
                raise ValueError("--limit must be between 1 and 500")
            result = list_payload(args)
        elif args.command == "inspect":
            result = inspect_payload(args)
        elif args.command == "wait":
            result = wait_payload(args)
        else:
            result = invoke_payload(args, smoke_test=args.command == "smoke-test")
        emit(result, args.json)
        return 0 if result.get("ok") else 1
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        emit(payload, getattr(args, "json", False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
