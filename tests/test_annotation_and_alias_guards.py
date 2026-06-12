"""Layer-4/6 preprocessing guards (src/preprocessing/pipeline.py).

- _build_alias_map: an alias shared by 2+ characters must stay banned even if
  a later character (or duplicate alias entry) claims it again — a re-added
  mapping made _replace_aliases rewrite the phrase to the wrong name across
  the whole book text.
- _llm_annotate_chapter: a parseable-but-misnumbered LLM response (string
  scene_numbers, empty list, out-of-range numbers) used to blank every
  segment AND get checkpointed under a valid fingerprint, permanently.
"""

from __future__ import annotations

import pytest

import src.llm_client as llm_client
from src.preprocessing.pipeline import _build_alias_map, _llm_annotate_chapter


# ── alias tombstone ──────────────────────────────────────────────


def test_shared_alias_stays_banned_for_third_character():
    chars = [
        {"canonical_name": "Doctor Manette", "aliases": ["the old man"]},
        {"canonical_name": "Jarvis Lorry", "aliases": ["the old man"]},
        {"canonical_name": "Jeremiah Cruncher", "aliases": ["the old man"]},
    ]
    assert "the old man" not in _build_alias_map(chars)


def test_duplicate_alias_entry_does_not_resurrect_ban():
    chars = [
        {"canonical_name": "A Person", "aliases": ["the prisoner"]},
        {"canonical_name": "B Person", "aliases": ["the prisoner", "the prisoner"]},
    ]
    assert "the prisoner" not in _build_alias_map(chars)


def test_unambiguous_alias_still_mapped():
    chars = [
        {"canonical_name": "Madame Defarge", "aliases": ["the knitting woman"]},
        {"canonical_name": "Jarvis Lorry", "aliases": ["the man of business"]},
    ]
    m = _build_alias_map(chars)
    assert m["the knitting woman"] == "Madame Defarge"
    assert m["the man of business"] == "Jarvis Lorry"


# ── annotation matching guards ───────────────────────────────────


def _segs(n: int) -> list[dict]:
    return [{"text": f"segment text {i}"} for i in range(n)]


def _stub_llm(monkeypatch, annotations):
    monkeypatch.setattr(llm_client, "generate_json", lambda *a, **k: {"annotations": annotations})


def test_string_scene_numbers_are_matched(monkeypatch):
    _stub_llm(monkeypatch, [
        {"scene_number": "1", "scene_summary": "first"},
        {"scene_number": "2", "scene_summary": "second"},
    ])
    segs = _llm_annotate_chapter("Title", "Ch 1", _segs(2), [])
    assert segs[0]["scene_summary"] == "first"
    assert segs[1]["scene_summary"] == "second"


def test_out_of_range_numbers_raise_instead_of_blanking(monkeypatch):
    _stub_llm(monkeypatch, [{"scene_number": 100, "scene_summary": "x"}])
    with pytest.raises(ValueError):
        _llm_annotate_chapter("Title", "Ch 1", _segs(2), [])


def test_empty_annotation_list_raises(monkeypatch):
    _stub_llm(monkeypatch, [])
    with pytest.raises(ValueError):
        _llm_annotate_chapter("Title", "Ch 1", _segs(2), [])


def test_unmatched_segment_keeps_existing_fields(monkeypatch):
    _stub_llm(monkeypatch, [{"scene_number": 1, "scene_summary": "new summary"}])
    segs = _segs(2)
    segs[1]["scene_summary"] = "preexisting"
    segs[1]["simplified_text"] = "kept"
    out = _llm_annotate_chapter("Title", "Ch 1", segs, [])
    assert out[0]["scene_summary"] == "new summary"
    assert out[1]["scene_summary"] == "preexisting"
    assert out[1]["simplified_text"] == "kept"
