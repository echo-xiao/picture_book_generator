"""Appendix point-fixes from the review.

#2 quality endpoints take the regen mutex (don't score an image being replaced).
#3 character rename drops stale chapter consistency caches.
"""

from __future__ import annotations

import src.routes.editor as editor
from src.routes.helpers import _active_regens


def test_segment_quality_409_during_regen(client, monkeypatch):
    monkeypatch.setattr(
        "src.routes.generation._load_json",
        lambda bid, fn: {"segments": [{"id": 0, "chapter_idx": 0}]} if fn == "analysis.json" else {},
    )
    _active_regens.add(("b", "segment", 0))
    try:
        assert client.post("/api/book/b/segment/0/quality").status_code == 409
    finally:
        _active_regens.discard(("b", "segment", 0))


def test_special_quality_409_during_regen(client):
    _active_regens.add(("b", "special", "book_cover:0"))
    try:
        assert client.post("/api/book/b/special/book_cover/quality").status_code == 409
    finally:
        _active_regens.discard(("b", "special", "book_cover:0"))


def test_rename_drops_chapter_consistency(monkeypatch, tmp_path):
    monkeypatch.setattr(editor, "GENERATED_DIR", tmp_path)
    monkeypatch.setattr(editor, "_load_json", lambda bid, fn: {})
    monkeypatch.setattr(editor, "_save_json", lambda *a, **k: None)
    ch = tmp_path / "b" / "chapters" / "ch00"
    ch.mkdir(parents=True)
    cons = ch / "consistency.json"
    cons.write_text("{}")

    editor._cascade_character_rename("b", "Alice", "Alicia")

    assert not cons.exists(), "rename must invalidate the chapter consistency cache"
