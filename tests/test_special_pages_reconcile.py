"""Root cause I: special-page records reconcile against current analysis.

special_pages.json is a derived snapshot. When it was returned as-is, a
character/scene rename (which updates analysis but not special_pages) left the
cover record pointing at the OLD name → regen looked up a sheet by a name whose
file had been renamed → the character lost its reference. Same for scene
backgrounds.

Fix = ONE reconciliation point: load_special_records always recomputes the
derived fields from current analysis and overlays ONLY the fields the user
explicitly edited (_edited). No per-rename special-page cascade.
"""

from __future__ import annotations

import src.routes.editor as editor


def _fake_store(overrides=None):
    """A _load_json stub backed by an in-memory dict of preprocess files."""
    store = {
        "analysis.json": {"segments": [
            {"id": 0, "chapter_idx": 0, "characters_in_scene": ["Alicia"],
             "scene_background": "the new forest", "scene_summary": "Alicia walks"},
        ]},
        "meta.json": {"title": "Book"},
        "chapter_segments.json": {"0": {"chapter_title": "Chapter 1", "segment_ids": [0]}},
        "llm_locations.json": {"locations": []},
        # Stale stored record (pre-rename, full preprocess derive — no _edited).
        "special_pages.json": {"pages": {
            "chapter_cover:0": {"characters_in_scene": ["Alice"],
                                "scene_background": "the old forest",
                                "subtitle_text": "A Picture Book"},
        }},
    }
    if overrides:
        store.update(overrides)
    return lambda book_id, fn: store.get(fn)


def test_rename_propagates_via_reconciliation(monkeypatch):
    monkeypatch.setattr(editor, "_load_json", _fake_store())
    records = editor.load_special_records("b")
    cc = records["chapter_cover:0"]
    # Derived fresh from current analysis — the renamed character/scene win.
    assert cc["characters_in_scene"] == ["Alicia"]
    assert "old forest" not in cc["scene_background"]


def test_user_edited_field_is_preserved(monkeypatch):
    edited_store = _fake_store({"special_pages.json": {"pages": {
        "chapter_cover:0": {"subtitle_text": "My Custom Subtitle", "_edited": ["subtitle_text"]},
    }}})
    monkeypatch.setattr(editor, "_load_json", edited_store)
    cc = editor.load_special_records("b")["chapter_cover:0"]
    # The explicitly edited field is kept …
    assert cc["subtitle_text"] == "My Custom Subtitle"
    # … but un-edited derived fields still refresh from analysis.
    assert cc["characters_in_scene"] == ["Alicia"]
