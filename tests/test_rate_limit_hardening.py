"""Rate limiter spoofing + memory hardening (src/app.py, H2).

High-risk review finding: the limiter keyed on the LEFTMOST X-Forwarded-For
entry — client-supplied — so rotating the header bypassed every limit AND
minted an unbounded number of buckets (the old cleanup removed only EMPTY
deques, which one-shot keys never become).
"""

from __future__ import annotations

import time
from collections import deque
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.app import _client_ip, _rate_buckets, app


def _req(xff: str | None, host: str = "10.0.0.5"):
    headers = {"x-forwarded-for": xff} if xff is not None else {}
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=host))


class TestClientIp:
    def test_rightmost_public_wins(self):
        # The proxy APPENDS the verified client; everything left is spoofable.
        assert _client_ip(_req("6.6.6.6, 93.184.216.34")) == "93.184.216.34"

    def test_internal_hops_are_skipped(self):
        # In-container Next.js proxy adds loopback hops to the right.
        assert _client_ip(_req("6.6.6.6, 93.184.216.34, 127.0.0.1")) == "93.184.216.34"

    def test_garbage_and_private_fall_back_to_socket(self):
        assert _client_ip(_req("not-an-ip, 10.1.2.3")) == "10.0.0.5"

    def test_no_header_uses_socket(self):
        assert _client_ip(_req(None)) == "10.0.0.5"


def test_rotating_spoofed_prefix_does_not_bypass(monkeypatch):
    """Rotating the attacker-controlled left side must NOT reset the limit:
    the trusted rightmost entry (appended by the proxy) stays the key.
    (34.x is genuinely public — Python 3.12+ marks the TEST-NET documentation
    ranges as private, which would fall through to the socket host.)"""
    monkeypatch.setattr("src.core.db.save_feedback", lambda *a, **k: True)
    client = TestClient(app)
    codes = [
        client.post(
            "/api/feedback", json={"message": "hi"},
            headers={"x-forwarded-for": f"{i}.{i}.{i}.{i}, 34.86.100.77"},
        ).status_code
        for i in range(1, 8)
    ]
    assert 429 in codes, "spoofed-prefix rotation must not evade the limit"


def test_bucket_pruning_reclaims_stale_one_shot_keys(monkeypatch):
    """One-shot keys (non-empty deques) must be reclaimed once stale —
    previously they accumulated forever under header rotation."""
    monkeypatch.setattr("src.core.db.save_feedback", lambda *a, **k: True)
    stale_ts = time.time() - 3600
    for i in range(5001):
        _rate_buckets[(f"stale-{i}", "/api/feedback")] = deque([stale_ts])
    try:
        client = TestClient(app)
        client.post("/api/feedback", json={"message": "hi"},
                    headers={"x-forwarded-for": "34.86.100.99"})
        assert len(_rate_buckets) < 100, "stale non-empty buckets must be swept"
    finally:
        for k in [k for k in _rate_buckets if str(k[0]).startswith("stale-")]:
            _rate_buckets.pop(k, None)
