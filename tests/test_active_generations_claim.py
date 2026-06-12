"""Chapter-generation in-flight claim must not leak (routes/generation.py).

Low-risk review finding: the key was added to _active_generations BEFORE the
progress-file init; if that init raised (disk full), nothing ever discarded
the key — the chapter answered "already_generating" until process restart.
"""

from __future__ import annotations

import pathlib

import pytest


def test_failed_kickoff_releases_the_chapter_claim(client, monkeypatch, tmp_path):
    monkeypatch.setattr("src.routes.generation.GENERATED_DIR", tmp_path)
    (tmp_path / "somebook" / "preprocess").mkdir(parents=True)

    from src.routes import generation as gen
    gen._active_generations.discard(("somebook", 0))

    real_write = pathlib.Path.write_text

    def failing_write(self, *args, **kwargs):
        if self.name == "progress.json":
            raise OSError("disk full")
        return real_write(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", failing_write)

    resp = client.post("/api/book/somebook/chapter/0/generate")
    assert resp.status_code == 500
    # The regression: the claim must NOT survive the failed kickoff —
    # otherwise every retry gets "already_generating" until a restart.
    assert ("somebook", 0) not in gen._active_generations
