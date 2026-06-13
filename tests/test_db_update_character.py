"""db.update_character must report whether anything matched (core/db.py).

Low-risk review finding: it returned True unconditionally, so the editor's
Mongo-fallback path answered {"status": "updated"} (and ran the whole rename
cascade) for characters that exist nowhere, instead of a 404.
"""

from __future__ import annotations


from src.core import db


class _Result:
    def __init__(self, matched: int):
        self.matched_count = matched


class _Characters:
    def __init__(self, matched: int):
        self._matched = matched
        self.calls: list = []

    def update_one(self, flt, update):
        self.calls.append((flt, update))
        return _Result(self._matched)


class _DB:
    def __init__(self, matched: int):
        self.characters = _Characters(matched)


def test_update_character_false_when_no_match(monkeypatch):
    fake = _DB(matched=0)
    monkeypatch.setattr(db, "_get_db", lambda: fake)
    assert db.update_character("b", "Nobody", {"gender": "male"}) is False
    assert fake.characters.calls  # it did try


def test_update_character_true_when_matched(monkeypatch):
    fake = _DB(matched=1)
    monkeypatch.setattr(db, "_get_db", lambda: fake)
    assert db.update_character("b", "Jay Gatsby", {"gender": "male"}) is True


def test_update_character_false_when_db_down(monkeypatch):
    monkeypatch.setattr(db, "_get_db", lambda: None)
    assert db.update_character("b", "Jay Gatsby", {"gender": "male"}) is False


def test_editor_404_for_character_missing_everywhere(client, monkeypatch):
    """End-to-end: file layer empty + Mongo matches nothing → PUT must 404,
    not pretend it updated."""
    monkeypatch.setattr("src.routes.editor._load_json", lambda *a: {})
    monkeypatch.setattr("src.core.db.is_available", lambda: True)
    monkeypatch.setattr("src.core.db.update_character", lambda *a, **k: False)

    resp = client.put(
        "/api/book/somebook/preprocess/characters/Nobody",
        json={"gender": "male"},
    )
    assert resp.status_code == 404
