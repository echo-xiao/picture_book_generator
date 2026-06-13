"""Root cause B: ONE Gemini backoff policy (gemini_backend.call_gemini_with_backoff).

Three callsites used to each implement their own retry loop with different
params, none distinguishing a transient 429 from a free-tier zero-quota 429
(which can NEVER succeed). The free-tier key — the most common public case —
burned 5–15s of sleeps before failing.
"""

from __future__ import annotations

import re
import pathlib

import pytest

import src.gemini_backend as gb


@pytest.fixture()
def no_real_sleep(monkeypatch):
    waits = []
    monkeypatch.setattr(gb.time, "sleep", lambda s: waits.append(s))
    return waits


FREE_TIER = ("429 RESOURCE_EXHAUSTED ... quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier, "
             "model: gemini-3.1-flash-image. Please retry in 48.8s")


def test_free_tier_fails_fast_no_sleep(no_real_sleep):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise RuntimeError(FREE_TIER)

    with pytest.raises(RuntimeError):
        gb.call_gemini_with_backoff(fn, max_retries=3)
    assert calls["n"] == 1            # no retry — it can never succeed
    assert no_real_sleep == []        # and zero sleeping


def test_transient_429_retries_then_raises(no_real_sleep):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise RuntimeError("429 rate limit, please slow down")

    with pytest.raises(RuntimeError):
        gb.call_gemini_with_backoff(fn, max_retries=3, base=5.0)
    assert calls["n"] == 3            # retried up to the limit
    assert len(no_real_sleep) == 2    # slept between attempts


def test_retry_after_is_honoured(no_real_sleep):
    def fn():
        raise RuntimeError("429 RESOURCE_EXHAUSTED. Please retry in 30s")

    with pytest.raises(RuntimeError):
        gb.call_gemini_with_backoff(fn, max_retries=2, base=5.0)
    # First (and only) backoff waits ~30s (server's Retry-After), not base 5s.
    assert no_real_sleep and abs(no_real_sleep[0] - 30.0) < 0.01


def test_non_transient_raises_immediately(no_real_sleep):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise ValueError("malformed request")

    with pytest.raises(ValueError):
        gb.call_gemini_with_backoff(fn, max_retries=3)
    assert calls["n"] == 1
    assert no_real_sleep == []


def test_success_returns_value(no_real_sleep):
    assert gb.call_gemini_with_backoff(lambda: "ok", max_retries=3) == "ok"


def test_grep_no_retry_sleep_outside_backoff():
    """Backoff sleeps live only in gemini_backend. The one remaining time.sleep
    elsewhere (illustration page throttle) is proactive pacing, not a retry."""
    root = pathlib.Path(__file__).resolve().parent.parent / "src"
    offenders = []
    for f in root.rglob("*.py"):
        if f.name == "gemini_backend.py":
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if re.search(r"\btime\.sleep\(", line) and "throttle" not in line.lower():
                # allow only a sleep whose own comment/nearby marks it a throttle
                offenders.append(f"{f.relative_to(root)}:{i}: {line.strip()}")
    # The inter-page throttle is the only allowed one (illustration.py).
    assert all("illustration.py" in o for o in offenders), offenders
