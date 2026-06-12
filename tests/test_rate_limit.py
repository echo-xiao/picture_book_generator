"""Per-IP rate limiting on public POST endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.app import app


def _post_feedback(client: TestClient, ip: str):
    return client.post("/api/feedback", json={"message": "hi"}, headers={"x-forwarded-for": ip})


def test_feedback_rate_limited_after_quota(monkeypatch):
    # Don't actually persist during the test.
    monkeypatch.setattr("src.core.db.save_feedback", lambda *a, **k: True)
    client = TestClient(app)
    # A genuinely PUBLIC ip: the limiter keys on the rightmost public XFF
    # entry, and Python 3.12+ classifies the TEST-NET documentation ranges
    # (203.0.113.x) as private — those fall through to the socket host and
    # every test would share one bucket.
    ip = "34.10.113.10"  # unique IP so other tests don't share the bucket
    codes = [_post_feedback(client, ip).status_code for _ in range(7)]
    assert codes[0] != 429, "first request must be allowed"
    assert 429 in codes, "exceeding the quota must yield 429"


def test_rate_limit_is_per_ip(monkeypatch):
    monkeypatch.setattr("src.core.db.save_feedback", lambda *a, **k: True)
    client = TestClient(app)
    # Exhaust one IP's quota.
    for _ in range(7):
        _post_feedback(client, "34.10.113.20")
    # A different IP is unaffected.
    assert _post_feedback(client, "34.10.113.21").status_code != 429
