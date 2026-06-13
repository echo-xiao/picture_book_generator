"""fetch-url response size cap (routes/books.py, H3).

High-risk review finding: the body was read un-streamed with no size limit —
one URL serving gigabytes (or a slow infinite stream within the 30s timeout)
OOM'd the single Cloud Run instance, taking all in-flight generation state
with it. The fetch now streams and aborts past MAX_FETCH_BYTES.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import HTTPException

from src.routes.books import MAX_FETCH_BYTES, _fetch_url_text
# Bound at import time — the autouse no_dns fixture below replaces the module
# attribute, but TestResolveSafeIp needs the real function.
from src.routes.books import _resolve_safe_ip as _real_resolve_safe_ip


@pytest.fixture(autouse=True)
def no_dns(monkeypatch):
    """Pin DNS so the SSRF resolver never touches the network."""
    monkeypatch.setattr("src.routes.books._resolve_safe_ip", lambda host: "93.184.216.34")


def _fetch(transport: httpx.MockTransport) -> str:
    return asyncio.run(_fetch_url_text("http://example.com/book.txt", transport=transport))


def test_small_body_passes_through():
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text="Title: A Book\nhello"))
    assert "hello" in _fetch(transport)


def test_oversized_body_is_aborted_mid_stream():
    big = b"x" * (MAX_FETCH_BYTES + 1)
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=big))
    with pytest.raises(HTTPException) as exc:
        _fetch(transport)
    assert exc.value.status_code == 413


def test_oversized_content_length_rejected_before_reading():
    # Header-based early reject: declare 11 MB without sending it.
    def handler(req):
        resp = httpx.Response(200, content=b"")
        resp.headers["content-length"] = str(MAX_FETCH_BYTES + 1)
        return resp
    with pytest.raises(HTTPException) as exc:
        _fetch(httpx.MockTransport(handler))
    assert exc.value.status_code == 413


def test_redirect_then_capped_body():
    """The cap must hold across redirect hops too."""
    def handler(req):
        if req.url.path == "/book.txt":
            return httpx.Response(302, headers={"location": "http://example.com/real.txt"})
        return httpx.Response(200, content=b"x" * (MAX_FETCH_BYTES + 1))
    with pytest.raises(HTTPException) as exc:
        _fetch(httpx.MockTransport(handler))
    assert exc.value.status_code == 413


class TestResolveSafeIp:
    """Cloud Run has no outbound IPv6 — picking getaddrinfo's first entry
    (an AAAA there) hung every fetch to a dual-stack host (gutenberg.org!)
    until the proxy cut it at 30s. IPv4 must win when present."""

    @staticmethod
    def _info(family, addr):
        import socket
        return (family, socket.SOCK_STREAM, 6, "", (addr, 0))

    def test_prefers_ipv4_even_when_ipv6_listed_first(self, monkeypatch):
        import socket
        monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: [
            self._info(socket.AF_INET6, "2610:28:3090:3000:0:bad:cafe:47"),
            self._info(socket.AF_INET, "152.19.134.47"),
        ])
        assert _real_resolve_safe_ip("www.gutenberg.org") == "152.19.134.47"

    def test_v6_only_host_still_resolves(self, monkeypatch):
        import socket
        monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: [
            self._info(socket.AF_INET6, "2001:4860:4860::8888"),
        ])
        assert _real_resolve_safe_ip("v6only.example") == "2001:4860:4860::8888"

    def test_private_ipv6_is_still_rejected(self, monkeypatch):
        import socket
        monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: [
            self._info(socket.AF_INET6, "::1"),
            self._info(socket.AF_INET, "152.19.134.47"),
        ])
        with pytest.raises(HTTPException) as exc:
            _real_resolve_safe_ip("evil.example")
        assert exc.value.status_code == 400
