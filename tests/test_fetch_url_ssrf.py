"""SSRF / DNS-rebinding guards for the /api/fetch-url endpoint."""

from __future__ import annotations

import socket

import pytest
from fastapi import HTTPException

from src.routes.books import _resolve_safe_ip


def _fake_getaddrinfo(*addrs):
    """Build a getaddrinfo stub returning the given IP strings."""
    def _stub(host, port, *a, **kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0)) for ip in addrs]
    return _stub


@pytest.mark.parametrize("addr", [
    "127.0.0.1",            # loopback
    "10.0.0.5",             # private
    "192.168.1.1",          # private
    "169.254.169.254",      # link-local — the cloud metadata server
    "0.0.0.0",              # unspecified
    "224.0.0.1",            # multicast
])
def test_internal_addresses_rejected(monkeypatch, addr):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo(addr))
    with pytest.raises(HTTPException) as exc:
        _resolve_safe_ip("evil.example.com")
    assert exc.value.status_code == 400


def test_public_address_allowed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("8.8.8.8"))
    assert _resolve_safe_ip("dns.google") == "8.8.8.8"


def test_any_internal_among_many_rejects(monkeypatch):
    # A name resolving to BOTH a public and an internal IP must be rejected —
    # otherwise an attacker hides the internal address behind a public one.
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("8.8.8.8", "10.1.2.3"))
    with pytest.raises(HTTPException):
        _resolve_safe_ip("rebind.example.com")


def test_unresolvable_host_rejected(monkeypatch):
    def _boom(*a, **kw):
        raise socket.gaierror("nope")
    monkeypatch.setattr(socket, "getaddrinfo", _boom)
    with pytest.raises(HTTPException) as exc:
        _resolve_safe_ip("does-not-exist.invalid")
    assert exc.value.status_code == 400
