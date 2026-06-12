"""Mongo-first reads must not shadow a newer local file (helpers.py, H4).

High-risk review finding: _save_json writes Mongo best-effort — a blip leaves
the file updated but the doc stale, and Mongo-first reads then served the old
doc forever (edits "saved" but reverting on refresh, the generation subprocess
working from stale data). _load_json now prefers a clearly-newer file and
heals the doc from it.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

import pytest

from src.routes import helpers


@pytest.fixture()
def book_file(monkeypatch, tmp_path):
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)
    pre = tmp_path / "somebook" / "preprocess"
    pre.mkdir(parents=True)
    path = pre / "analysis.json"
    path.write_text(json.dumps({"segments": ["FRESH FILE DATA"]}))
    return path


def _mock_mongo(monkeypatch, data, updated_at_iso, healed: list):
    monkeypatch.setattr(
        "src.core.db.load_preprocess_file_with_meta",
        lambda book_id, filename: (data, updated_at_iso),
    )
    monkeypatch.setattr(
        "src.core.db.save_preprocess_file",
        lambda book_id, filename, d: healed.append((filename, d)) or True,
    )


def test_newer_file_wins_and_heals_the_doc(monkeypatch, book_file):
    healed: list = []
    stale_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    _mock_mongo(monkeypatch, {"segments": ["STALE DOC DATA"]}, stale_iso, healed)

    result = helpers._load_json("somebook", "analysis.json")

    assert result == {"segments": ["FRESH FILE DATA"]}, "newer file must win over stale doc"
    assert healed and healed[0][1] == {"segments": ["FRESH FILE DATA"]}, "doc must be healed from the file"


def test_fresh_doc_still_wins_over_old_file(monkeypatch, book_file):
    healed: list = []
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    _mock_mongo(monkeypatch, {"segments": ["DOC DATA"]}, future_iso, healed)

    result = helpers._load_json("somebook", "analysis.json")

    assert result == {"segments": ["DOC DATA"]}, "Mongo-first stands when the doc is current"
    assert not healed


def test_doc_without_timestamp_keeps_mongo_first(monkeypatch, book_file):
    healed: list = []
    _mock_mongo(monkeypatch, {"segments": ["DOC DATA"]}, None, healed)
    assert helpers._load_json("somebook", "analysis.json") == {"segments": ["DOC DATA"]}
    assert not healed


def test_file_fallback_when_mongo_empty(monkeypatch, book_file):
    monkeypatch.setattr("src.core.db.load_preprocess_file_with_meta", lambda *a: None)
    assert helpers._load_json("somebook", "analysis.json") == {"segments": ["FRESH FILE DATA"]}
