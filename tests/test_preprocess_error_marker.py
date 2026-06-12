"""Preprocess crash path must leave an error marker (routes/books.py).

Low-risk review finding: timeout and non-zero-exit already wrote error.json,
but a crash before/at subprocess spawn only logged — the progress endpoint
then reported "processing" forever and both loading screens spun until the
user gave up.
"""

from __future__ import annotations

import asyncio
import json

import pytest


def test_spawn_crash_writes_error_marker(monkeypatch, tmp_path):
    monkeypatch.setattr("src.routes.books.GENERATED_DIR", tmp_path)

    async def boom(*args, **kwargs):
        raise OSError("spawn failed")

    monkeypatch.setattr("asyncio.create_subprocess_exec", boom)

    from src.routes.books import _run_preprocess
    asyncio.run(_run_preprocess("somebook", tmp_path / "in.txt"))

    err = json.loads((tmp_path / "somebook" / "preprocess" / "error.json").read_text())
    assert "spawn failed" in err["error"]
    assert err["returncode"] == -1


def test_progress_endpoint_reports_the_crash(client, monkeypatch, tmp_path):
    """The marker written by the crash path must surface as status=error so
    the frontend stops polling and shows the failure."""
    monkeypatch.setattr("src.routes.books.GENERATED_DIR", tmp_path)

    async def boom(*args, **kwargs):
        raise OSError("spawn failed")

    monkeypatch.setattr("asyncio.create_subprocess_exec", boom)

    from src.routes.books import _run_preprocess
    asyncio.run(_run_preprocess("somebook", tmp_path / "in.txt"))

    resp = client.get("/api/book/somebook/preprocess/progress")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "spawn failed" in body["error"]
