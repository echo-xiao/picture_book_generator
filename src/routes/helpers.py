"""Shared utility functions for route handlers."""

from __future__ import annotations

import json
from typing import Any

from src.config import GENERATED_DIR


def _load_json(book_id: str, filename: str) -> dict | list | None:
    path = GENERATED_DIR / book_id / "preprocess" / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(book_id: str, filename: str, data: Any) -> None:
    path = GENERATED_DIR / book_id / "preprocess" / filename
    path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
