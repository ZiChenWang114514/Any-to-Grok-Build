#!/usr/bin/env python3
"""Read-only diagnostics for a local Grok Build CLI installation and session."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable


KNOWN_FILES = ("summary.json", "signals.json", "updates.jsonl", "chat_history.jsonl")
DEFAULT_GROK = Path.home() / ".grok" / "bin" / "grok.exe"


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def grok_home() -> Path:
    return Path(os.environ.get("GROK_HOME", Path.home() / ".grok")).expanduser()


def locate_executable(explicit: str | None) -> Path | None:
    choices = [explicit, os.environ.get("GROK_EXE"), str(DEFAULT_GROK), shutil.which("grok")]
    for item in choices:
        if item:
            path = Path(item).expanduser()
            if path.is_file():
                return path
    return None


def json_file(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def tail_lines(path: Path, maximum_bytes: int = 1_500_000) -> list[str]:
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


def latest_non_completed_total_tokens(paths: Iterable[Path]) -> int | None:
    for path in paths:
        for line in reversed(tail_lines(path)):
            if "turn_completed" in line.lower():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            numbers = [v for v in values_named(item, {"totalTokens"}) if isinstance(v, int)]
            if numbers:
                return numbers[-1]
    return None


def recent_markers(paths: Iterable[Path]) -> list[str]:
    markers: list[str] = []
    for path in paths:
        tail = "\n".join(tail_lines(path)[-250:]).lower()
        for marker in ("turn_completed", "toolcall", "tool_call", "final"):
            if marker in tail and marker not in markers:
                markers.append(marker)
    return markers


def find_session(session_id: str, home: Path) -> list[Path]:
    root = home / "sessions"
    if not root.is_dir():
        return []
    return sorted(path for path in root.glob(f"*/{session_id}") if path.is_dir())


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


def status(args: argparse.Namespace) -> int:
    home = grok_home()
    executable = locate_executable(args.grok)
    version = None
    version_error = None
    if executable:
        try:
            completed = subprocess.run(
                [str(executable), "--version"], capture_output=True, text=True, timeout=10, check=False
            )
            version = (completed.stdout or completed.stderr).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            version_error = str(exc)
    sessions_root = home / "sessions"
    active = json_file(home / "active_sessions.json")
    active_count = len(active) if isinstance(active, (dict, list)) else None
    emit(
        {
            "status": "ready" if executable else "grok_executable_missing",
            "grok_home": str(home),
            "grok_executable": str(executable) if executable else None,
            "version": version,
            "version_error": version_error,
            "sessions_root": str(sessions_root),
            "sessions_root_exists": sessions_root.is_dir(),
            "active_sessions_index_exists": (home / "active_sessions.json").is_file(),
            "active_sessions_index_count": active_count,
        },
        args.json,
    )
    return 0 if executable else 2


def inspect(args: argparse.Namespace) -> int:
    home = grok_home()
    matches = find_session(args.session_id, home)
    if len(matches) != 1:
        emit(
            {
                "status": "session_not_found" if not matches else "session_ambiguous",
                "session_id": args.session_id,
                "matches": [str(path) for path in matches],
                "sessions_root": str(home / "sessions"),
            },
            args.json,
        )
        return 3
    session_dir = matches[0]
    signals = json_file(session_dir / "signals.json")
    summary = json_file(session_dir / "summary.json")
    context_tokens = list(values_named(signals, {"contextTokensUsed"})) if signals is not None else []
    context_usage = list(values_named(signals, {"contextWindowUsage"})) if signals is not None else []
    context_window_tokens = list(values_named(signals, {"contextWindowTokens"})) if signals is not None else []
    compactions = list(values_named(signals, {"compactionCount"})) if signals is not None else []
    event_paths = [session_dir / "updates.jsonl", session_dir / "chat_history.jsonl"]
    emit(
        {
            "status": "found",
            "session_id": args.session_id,
            "session_dir": str(session_dir),
            "session_owner_encoded": session_dir.parent.name,
            "files": file_snapshot(session_dir),
            "signals_contextTokensUsed": context_tokens[-1] if context_tokens else None,
            "signals_contextWindowUsage": context_usage[-1] if context_usage else None,
            "signals_contextWindowTokens": context_window_tokens[-1] if context_window_tokens else None,
            "signals_compactionCount": compactions[-1] if compactions else None,
            "latest_non_turn_completed_totalTokens": latest_non_completed_total_tokens(event_paths),
            "recent_event_markers": recent_markers(event_paths),
            "summary_available": summary is not None,
        },
        args.json,
    )
    return 0


def wait_for_stability(args: argparse.Namespace) -> int:
    if not 1 <= args.seconds <= 60:
        raise ValueError("--seconds must be between 1 and 60")
    matches = find_session(args.session_id, grok_home())
    if len(matches) != 1:
        inspect(args)
        return 3
    session_dir = matches[0]
    before = file_snapshot(session_dir)
    time.sleep(args.seconds)
    after = file_snapshot(session_dir)
    emit(
        {
            "status": "stable" if before == after else "changed",
            "session_id": args.session_id,
            "seconds": args.seconds,
            "before": before,
            "after": after,
            "note": "File stability alone does not prove that a Grok turn has finished.",
        },
        args.json,
    )
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Read-only Grok Build session diagnostics")
    subparsers = result.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--grok")
    status_parser.add_argument("--json", action="store_true")
    status_parser.set_defaults(handler=status)
    for command, handler in (("inspect", inspect), ("wait", wait_for_stability)):
        child = subparsers.add_parser(command)
        child.add_argument("--session-id", required=True)
        if command == "wait":
            child.add_argument("--seconds", type=int, default=10)
        child.add_argument("--json", action="store_true")
        child.set_defaults(handler=handler)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
