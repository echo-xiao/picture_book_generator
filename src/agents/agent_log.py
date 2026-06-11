"""Agent activity log for tracking multi-agent collaboration.

Writes timestamped log entries to a JSON file per chapter generation session.
Frontend polls these logs to display agent pipeline status and thinking process.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from src.config import GENERATED_DIR


def _atomic_write(path: Path, text: str) -> None:
    """Write via temp file + atomic rename — two processes (API server and the
    generate_chapter subprocess) append to this log concurrently, and a plain
    write_text could be read half-written or clobber a concurrent write."""
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, path)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _log_path(book_id: str, chapter_idx: int) -> Path:
    # Callers sometimes pass the chapter index as a string (e.g. derived from a
    # directory name like "ch01" -> "1"). Coerce defensively so the f"{:02d}"
    # format never raises ValueError — that exception was being swallowed by the
    # callers' try/except and silently dropping every QA/self-correct log entry.
    try:
        chapter_idx = int(chapter_idx)
    except (TypeError, ValueError):
        chapter_idx = 0
    p = GENERATED_DIR / book_id / "chapters" / f"ch{chapter_idx:02d}" / "agent_log.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def clear_log(book_id: str, chapter_idx: int) -> None:
    """Clear logs at the start of a new generation session."""
    path = _log_path(book_id, chapter_idx)
    _atomic_write(path, "[]")


def log_event(
    book_id: str,
    chapter_idx: int,
    agent: str,
    action: str,
    detail: str = "",
    result: str = "",
    status: str = "running",  # running | done | warn | error
) -> None:
    """Append an event to the agent log."""
    path = _log_path(book_id, chapter_idx)
    entries = []
    if path.exists():
        try:
            entries = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            entries = []

    entries.append({
        "ts": time.time(),
        "agent": agent,
        "action": action,
        "detail": detail,
        "result": result,
        "status": status,
    })
    _atomic_write(path, json.dumps(entries, ensure_ascii=False))


def get_log(book_id: str, chapter_idx: int) -> list[dict]:
    """Read all log entries for a chapter."""
    path = _log_path(book_id, chapter_idx)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
