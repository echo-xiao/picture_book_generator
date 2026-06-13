"""BYOK gate matrix (app.py BYOKMiddleware + _GEN_SUFFIXES).

With REQUIRE_USER_KEY on, every endpoint that spends LLM/image quota must 403
when no x-gemini-key header is supplied. The middleware rejects before any
route code runs, so these tests never touch MongoDB or Gemini.
"""

from __future__ import annotations

import pytest

GATED_POSTS = [
    "/api/generate",
    "/api/book/test-book/segment/0/regenerate",
    "/api/book/test-book/segment/0/simplify",
    "/api/book/test-book/segment/0/background",
    "/api/book/test-book/segment/0/summarize",
    "/api/book/test-book/segment/0/quality",
    "/api/book/test-book/chapter/0/generate",
    "/api/book/test-book/chapter/0/consistency",
    "/api/book/test-book/special/book_cover/regenerate",
    "/api/book/test-book/scenes/somewhere/regenerate",
    "/api/book/test-book/characters/someone/regenerate",
    "/api/book/test-book/preprocess/characters/someone/autofill",
]


@pytest.mark.parametrize("path", GATED_POSTS)
def test_generation_endpoints_403_without_key(client, require_user_key, path):
    resp = client.post(path)
    assert resp.status_code == 403, f"{path} not gated: {resp.status_code}"
    assert "Gemini API key" in resp.json()["detail"]


DEPENDS_GATED_POSTS = [
    # These four used to rely ONLY on the middleware's suffix match — a path
    # rename would have silently un-gated them. They now also carry a
    # Depends(_require_user_key) belt; prove it holds with the middleware
    # suffix list emptied.
    "/api/book/test-book/segment/0/quality",
    "/api/book/test-book/characters/someone/quality",
    "/api/book/test-book/chapter/0/consistency",
    "/api/book/test-book/preprocess/characters/someone/autofill",
]


@pytest.mark.parametrize("path", DEPENDS_GATED_POSTS)
def test_depends_belt_holds_without_middleware(client, require_user_key, monkeypatch, tmp_path, path):
    # Empty the BYOK suffix list so the middleware key-gate can't be what 403s —
    # the route's own Depends(_require_user_key) belt must. But with the gate on,
    # the ownership middleware now runs first; make "test-book" owned and present
    # the matching email so the request reaches the route belt instead of being
    # stopped at ownership.
    monkeypatch.setattr("src.app._GEN_SUFFIXES", ())
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)
    import json
    pre = tmp_path / "test-book" / "preprocess"
    pre.mkdir(parents=True)
    (pre / "user.json").write_text(json.dumps({"email": "owner@x.com"}))
    resp = client.post(path, headers={"X-User-Email": "owner@x.com"})
    assert resp.status_code == 403, f"{path} lost its Depends gate: {resp.status_code}"
    assert "Gemini API key" in resp.json()["detail"]


def test_non_generation_post_is_not_gated(client, require_user_key, monkeypatch, tmp_path):
    """Control: a non-generation path must NOT be blocked by the BYOK key-gate.
    regen-status only has a GET route, so the router answers 405 — the point is
    that it's not a middleware 403. The owner is set up and the matching email
    presented so the ownership gate (which DOES guard book writes) lets it
    through to the router; what's left is the 405, proving the BYOK suffix gate
    isn't over-blocking a non-generation POST."""
    import json
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)
    pre = tmp_path / "test-book" / "preprocess"
    pre.mkdir(parents=True)
    (pre / "user.json").write_text(json.dumps({"email": "owner@x.com"}))
    resp = client.post("/api/book/test-book/segment/0/regen-status",
                       headers={"X-User-Email": "owner@x.com"})
    assert resp.status_code == 405


def test_gate_off_lets_requests_through_middleware(client):
    """With REQUIRE_USER_KEY off (default in tests), the BYOK middleware must
    not block generation endpoints. The book id here is deliberately invalid
    so the request is stopped by BookIdValidationMiddleware (400) right after
    BYOK — proving we got past the gate without running any route code."""
    resp = client.post("/api/book/bad..id/segment/0/simplify")
    assert resp.status_code == 400


def test_invalid_book_id_rejected_even_with_gate_on(client, require_user_key):
    """BYOK runs before book-id validation; with the gate on and no key the
    403 wins. This pins the middleware ordering so a reorder can't silently
    expose path-traversal ids to gated routes."""
    resp = client.post("/api/book/bad..id/segment/0/simplify")
    assert resp.status_code == 403
