"""Root cause II: a best-effort write to authority data must not silently
report success.

Character rename writes the `characters` collection (the consistency hub that
load_characters — and thus all generation — reads FIRST) best-effort. When that
write failed, the endpoint still returned {"status": "updated"}: the hub kept
the old name while the file/analysis had the new one, and generation silently
used stale character data. The response must flag the divergence.

Only flagged when Mongo is REACHABLE but the write failed — a fully-down Mongo
is consistent (load_characters falls back to the updated file).
"""

from __future__ import annotations

import pytest

import src.routes.editor as editor


@pytest.fixture()
def book(monkeypatch, tmp_path):
    monkeypatch.setattr(editor, "GENERATED_DIR", tmp_path)
    store = {"llm_characters.json": {"characters": [{"canonical_name": "Alice", "gender": "female"}]}}
    monkeypatch.setattr(editor, "_load_json", lambda bid, fn: store.get(fn, {}))
    monkeypatch.setattr(editor, "_save_json", lambda *a, **k: None)
    return store


def _rename(client):
    return client.put("/api/book/b/preprocess/characters/Alice",
                      json={"canonical_name": "Alicia"})


def test_degraded_when_hub_reachable_but_write_fails(client, book, monkeypatch):
    monkeypatch.setattr("src.core.db.is_available", lambda: True)
    monkeypatch.setattr("src.core.db.update_character", lambda *a, **k: False)
    body = _rename(client).json()
    assert body["status"] == "updated"
    assert body.get("degraded") is True


def test_degraded_when_hub_write_raises(client, book, monkeypatch):
    monkeypatch.setattr("src.core.db.is_available", lambda: True)

    def _boom(*a, **k):
        raise RuntimeError("mongo blip")
    monkeypatch.setattr("src.core.db.update_character", _boom)
    body = _rename(client).json()
    assert body.get("degraded") is True


def test_not_degraded_when_hub_write_ok(client, book, monkeypatch):
    monkeypatch.setattr("src.core.db.is_available", lambda: True)
    monkeypatch.setattr("src.core.db.update_character", lambda *a, **k: True)
    body = _rename(client).json()
    assert body["status"] == "updated"
    assert not body.get("degraded")


def test_not_degraded_when_mongo_down(client, book, monkeypatch):
    # Fully-down Mongo is consistent: load_characters falls back to the updated
    # file, so no divergence — don't cry wolf.
    monkeypatch.setattr("src.core.db.is_available", lambda: False)
    monkeypatch.setattr("src.core.db.update_character", lambda *a, **k: False)
    body = _rename(client).json()
    assert not body.get("degraded")
