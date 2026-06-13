"""Per-user library isolation (A) + same-book reuse (B).

A: the library shows the viewer's OWN books (matched by the email they created
   them with) plus the public samples — not everyone's books.
B: re-submitting an already-fully-preprocessed book reuses it (status 'exists')
   instead of re-running the whole pipeline.
"""

from __future__ import annotations

import json

import pytest

import src.routes.books as books


@pytest.fixture()
def library(monkeypatch, tmp_path):
    monkeypatch.setattr(books, "GENERATED_DIR", tmp_path)
    # Ownership is read via helpers.book_owner_email (the single source); in prod
    # both modules share one GENERATED_DIR, but tests patch per-module.
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)
    monkeypatch.setattr("src.core.db.list_preprocess_books", lambda: [])
    monkeypatch.setattr(books, "_load_json", lambda bid, fn: {})
    monkeypatch.setenv("SAMPLE_BOOK_IDS", "the_great_gatsby")

    def _make(book_id, owner=None):
        pre = tmp_path / book_id / "preprocess"
        pre.mkdir(parents=True)
        (pre / "meta.json").write_text(json.dumps({"title": book_id}))
        if owner is not None:
            (pre / "user.json").write_text(json.dumps({"email": owner}))

    _make("the_great_gatsby")                       # public sample (no owner)
    _make("alice_book", owner="alice@x.com")        # alice's
    _make("bob_book", owner="bob@x.com")            # bob's
    return tmp_path


def _ids(client, **params):
    return {b["book_id"] for b in client.get("/api/books/preprocessed", params=params).json()}


def test_viewer_sees_own_plus_sample(client, library):
    assert _ids(client, email="alice@x.com") == {"the_great_gatsby", "alice_book"}


def test_viewer_does_not_see_others_books(client, library):
    got = _ids(client, email="alice@x.com")
    assert "bob_book" not in got


def test_no_email_sees_only_samples(client, library):
    assert _ids(client) == {"the_great_gatsby"}


def test_sample_marked_is_sample(client, library):
    rows = client.get("/api/books/preprocessed", params={"email": "alice@x.com"}).json()
    by_id = {r["book_id"]: r for r in rows}
    assert by_id["the_great_gatsby"]["is_sample"] is True
    assert by_id["alice_book"]["is_sample"] is False


def test_resubmit_complete_book_reuses(client, monkeypatch, tmp_path):
    monkeypatch.setattr(books, "GENERATED_DIR", tmp_path)
    text = "The Great Gatsby\nIn my younger and more vulnerable years..."
    book_id = books._compute_book_id(text)
    pre = tmp_path / book_id / "preprocess"
    pre.mkdir(parents=True)
    (pre / "analysis.json").write_text("{}")
    (pre / "run_status.json").write_text(json.dumps({"status": "complete"}))

    resp = client.post("/api/generate", json={"source_text": text, "config": {}})
    assert resp.status_code == 200
    assert resp.json() == {"book_id": book_id, "status": "exists"}
