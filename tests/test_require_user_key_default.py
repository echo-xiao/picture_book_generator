"""Security #1 — REQUIRE_USER_KEY fails SAFE (defaults to locked).

A forgotten/unset env var must default to True (BYOK gate ON), so a deploy that
omits the var can't accidentally open generation onto the project's own bill.
Only the explicit string "false" opens it.
"""

from __future__ import annotations

import importlib

import pytest


def _reload_config_with(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("REQUIRE_USER_KEY", raising=False)
    else:
        monkeypatch.setenv("REQUIRE_USER_KEY", value)
    import src.config as config
    return importlib.reload(config)


def test_default_is_locked_when_unset(monkeypatch):
    config = _reload_config_with(monkeypatch, None)
    assert config.REQUIRE_USER_KEY is True


@pytest.mark.parametrize("value", ["false", "False", "FALSE", " false ".strip()])
def test_only_explicit_false_opens(monkeypatch, value):
    config = _reload_config_with(monkeypatch, value)
    assert config.REQUIRE_USER_KEY is False


@pytest.mark.parametrize("value", ["true", "True", "1", "yes", "", "off", "no"])
def test_anything_else_stays_locked(monkeypatch, value):
    """Only the literal 'false' (any case) unlocks; every other value — including
    typos like 'off'/'no' and the empty string — fails safe to locked."""
    config = _reload_config_with(monkeypatch, value)
    assert config.REQUIRE_USER_KEY is True
