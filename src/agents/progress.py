"""Single source of truth for chapter-generation progress.json.

Every place that reports generation progress (the ADK pipeline, the
generate_chapter subprocess shell, and the Artist's per-page loop) writes
through `update_progress()` so the file is always merge-written (never clobbered)
and the `agent` badge stays stable across writes. Previously this logic was
copy-pasted in three places and one of them overwrote the file, dropping fields.
"""

from __future__ import annotations

import json
import os
import tempfile

from src.config import GENERATED_DIR


def update_progress(book_id: str, chapter_idx, **fields) -> None:
    """Merge `fields` into the chapter's progress.json (frontend polls this)."""
    # Callers sometimes derive chapter_idx from a dir name ("ch01" -> "1");
    # coerce so the f"{:02d}" format never raises.
    try:
        chapter_idx = int(chapter_idx)
    except (TypeError, ValueError):
        chapter_idx = 0
    progress_file = GENERATED_DIR / book_id / "chapters" / f"ch{chapter_idx:02d}" / "progress.json"
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if progress_file.exists():
        try:
            existing = json.loads(progress_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    existing.update(fields)
    # Atomic write: the API server and the generate_chapter subprocess both
    # write this file; a plain write_text could be read half-written or clobber
    # a concurrent write mid-flight. Write a temp file, then atomically rename.
    fd, tmp_path = tempfile.mkstemp(dir=progress_file.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(existing))
        os.replace(tmp_path, progress_file)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
