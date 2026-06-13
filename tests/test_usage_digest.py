"""Owner usage-digest endpoint: token-gated, emails a books+feedback summary.

Monitors real activity (books generated, feedback received) and pushes it to
the owner's inbox. Token-gated so only the owner can trigger it; unset
ADMIN_TOKEN means it can never be hit.
"""

from __future__ import annotations

import src.routes.books as books


def test_digest_403_without_admin_token(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    # Even with a token query param, an unset ADMIN_TOKEN must always 403.
    assert client.get("/api/admin/usage-digest", params={"token": "anything"}).status_code == 403


def test_digest_403_on_wrong_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    assert client.get("/api/admin/usage-digest", params={"token": "nope"}).status_code == 403


def test_digest_emails_and_returns_data(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    data = {
        "available": True,
        "new_books": [{"title": "Gatsby", "book_id": "gatsby-ab12", "created_at": "2026-06-12T10:00:00+00:00"}],
        "feedback": [{"email": "u@x.com", "message": "love it", "created_at": "2026-06-12T11:00:00+00:00"}],
        "total_books": 7,
    }
    monkeypatch.setattr("src.core.db.usage_since", lambda cutoff: data)
    sent = {}
    monkeypatch.setattr(books, "_send_owner_email",
                        lambda subject, body, **k: sent.update(subject=subject, body=body) or True)

    resp = client.get("/api/admin/usage-digest", params={"token": "s3cret", "hours": 24})
    assert resp.status_code == 200
    out = resp.json()
    assert out["emailed"] is True
    assert out["total_books"] == 7
    assert out["new_books"][0]["title"] == "Gatsby"
    # The emailed digest mentions the real activity.
    assert "Gatsby" in sent["body"]
    assert "love it" in sent["body"]


def test_format_digest_handles_mongo_down():
    body = books._format_usage_digest({"available": False}, 24)
    assert "unavailable" in body.lower()
