"""Security #2 — tenant isolation enforced framework-wide (app.py
BookOwnershipMiddleware).

A book records its creator's email (preprocess/user.json). Every mutation of an
existing book (any POST/PUT/PATCH/DELETE to /api/book/{id}/...) must come from
that owner. One middleware gates them all, so a stranger can't delete or
regenerate someone else's book — and a new write route added later is covered
without remembering to add a per-endpoint check.

These tests drive the gate through DELETE /api/book/{id}: DELETE is not a
generation suffix, so the BYOK key-gate doesn't pre-empt the ownership check the
way it would on a /regenerate path — letting us isolate ownership behavior.
"""

from __future__ import annotations

import json

import pytest


def _make_owned_book(tmp_path, monkeypatch, book_id: str, owner: str | None):
    """Point both GENERATED_DIR readers at a tmp tree and (optionally) stamp an
    owner into user.json. owner=None leaves the book unowned (no user.json)."""
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)
    monkeypatch.setattr("src.routes.books.GENERATED_DIR", tmp_path)
    pre = tmp_path / book_id / "preprocess"
    pre.mkdir(parents=True, exist_ok=True)
    if owner is not None:
        (pre / "user.json").write_text(json.dumps({"email": owner}), encoding="utf-8")


def test_stranger_cannot_delete_anothers_book(client, require_user_key, tmp_path, monkeypatch):
    _make_owned_book(tmp_path, monkeypatch, "b", owner="owner@example.com")
    resp = client.delete("/api/book/b", headers={"X-User-Email": "stranger@example.com"})
    assert resp.status_code == 403
    assert "another account" in resp.json()["detail"]


def test_missing_email_cannot_mutate(client, require_user_key, tmp_path, monkeypatch):
    _make_owned_book(tmp_path, monkeypatch, "b", owner="owner@example.com")
    resp = client.delete("/api/book/b")  # no X-User-Email at all
    assert resp.status_code == 403
    assert "another account" in resp.json()["detail"]


def test_unowned_book_is_locked_not_open(client, require_user_key, tmp_path, monkeypatch):
    """A book with no recorded owner (public sample / legacy) is locked against
    mutation rather than open to everyone — owner '' matches no caller."""
    _make_owned_book(tmp_path, monkeypatch, "b", owner=None)
    resp = client.delete("/api/book/b", headers={"X-User-Email": "anyone@example.com"})
    assert resp.status_code == 403
    assert "another account" in resp.json()["detail"]


def test_owner_passes_the_gate(client, require_user_key, tmp_path, monkeypatch):
    """The owner's email gets past ownership; the request then reaches the route
    (here a stubbed delete) instead of the 403."""
    _make_owned_book(tmp_path, monkeypatch, "b", owner="owner@example.com")

    async def _fake_delete(book_id):
        return True
    monkeypatch.setattr("src.routes.books.delete_book", _fake_delete)
    monkeypatch.setattr("src.routes.books._preprocess_running", lambda _bid: False)

    # Owner email matches; the route also carries its own BYOK key-gate, so a
    # key is supplied too. Case/whitespace must not matter — owner is normalized.
    resp = client.delete("/api/book/b", headers={
        "X-User-Email": "  Owner@Example.com ",
        "X-Gemini-Key": "k",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "deleted"


def test_gate_off_skips_ownership(client, tmp_path, monkeypatch):
    """With REQUIRE_USER_KEY off, ownership is not enforced (local owner running
    on the project's own backend is never locked out of their own files)."""
    _make_owned_book(tmp_path, monkeypatch, "b", owner="owner@example.com")

    async def _fake_delete(book_id):
        return True
    monkeypatch.setattr("src.routes.books.delete_book", _fake_delete)
    monkeypatch.setattr("src.routes.books._preprocess_running", lambda _bid: False)

    resp = client.delete("/api/book/b", headers={"X-User-Email": "stranger@example.com"})
    assert resp.status_code == 200, resp.text


def test_creation_endpoint_not_ownership_gated(client, require_user_key):
    """POST /api/generate creates a book — the path is /api/generate, not
    /api/book/{id}, so the ownership gate's regex never matches and creation is
    never blocked by it (BYOK still gates it; a key is supplied here). Whatever
    the route then does, the response must not be the ownership 403."""
    resp = client.post("/api/generate", headers={"X-Gemini-Key": "k"},
                       json={"source_text": "hello world", "config": {}})
    detail = resp.json().get("detail", "") if resp.headers.get("content-type", "").startswith("application/json") else ""
    assert "another account" not in detail
