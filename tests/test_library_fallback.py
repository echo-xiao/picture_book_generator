"""Library listing resilience (core/db.py + routes/books.py).

Medium-risk review finding: a Mongo connection that dropped AFTER the initial
ping made db.list_preprocess_books raise straight through — the only read
path without a broad except — and GET /api/books/preprocessed 500'd instead
of falling back to the disk scan.
"""

from __future__ import annotations

import json


from src.core import db


class _ExplodingColl:
    def aggregate(self, pipeline):
        raise RuntimeError("connection dropped mid-flight")


class _DB:
    preprocess_files = _ExplodingColl()


def test_list_preprocess_books_swallows_midflight_errors(monkeypatch):
    monkeypatch.setattr(db, "_get_db", lambda: _DB())
    assert db.list_preprocess_books() == []


def test_library_endpoint_falls_back_to_disk(client, monkeypatch, tmp_path):
    """Mongo path empty → the endpoint must serve books found on disk (for the
    owner, under the per-user isolation filter)."""
    monkeypatch.setattr("src.core.db.list_preprocess_books", lambda: [])
    monkeypatch.setattr("src.routes.books.GENERATED_DIR", tmp_path)
    # Ownership filter reads helpers.book_owner_email (single source); patch its
    # GENERATED_DIR too so the owner match resolves against the tmp tree.
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)
    pre = tmp_path / "somebook" / "preprocess"
    pre.mkdir(parents=True)
    (pre / "meta.json").write_text(json.dumps({"title": "Some Book", "num_chapters": 3}))
    (pre / "user.json").write_text(json.dumps({"email": "owner@x.com"}))

    resp = client.get("/api/books/preprocessed", params={"email": "owner@x.com"})
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert books[0]["book_id"] == "somebook"
    assert books[0]["title"] == "Some Book"
