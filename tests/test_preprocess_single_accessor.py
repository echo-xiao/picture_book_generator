"""Root cause 2 (framework): ONE read strategy for preprocess data.

Both stores (local file + MongoDB) are kept — file is fast IPC for the chapter
subprocess + PDF + polling, Mongo is the cross-instance/persistent authority.
The bug was never "two stores"; it was TWO READ STRATEGIES over them: the web
read (_load_json) healed toward a fresher file, the subprocess read open-coded a
parallel MCP→pymongo→file→heal ladder that drifted. Two readers, two behaviors,
divergent results.

This pins the framework fix: every preprocess reader resolves through the single
self-healing accessor helpers._load_json, so the heal logic exists in exactly
one place and can't drift again. The subprocess (AnalyzerAgent.load_preprocess)
delegates to it rather than re-implementing it.
"""

from __future__ import annotations

import pathlib
import re

import src.agents.analyzer as analyzer_mod
import src.routes.helpers as helpers
from src.agents.analyzer import AnalyzerAgent


def test_subprocess_resolves_every_file_through_the_shared_accessor(monkeypatch):
    """load_preprocess must return exactly what _load_json yields for each file
    — proving it delegates to the one accessor instead of its own read ladder.
    A unique sentinel per filename makes any bypass (a file read or pymongo tier
    that skipped the accessor) show up as a missing/wrong value."""
    seen: list[str] = []

    def _fake_load_json(book_id, filename, *a, **k):
        seen.append(filename)
        return {"_via": "accessor", "file": filename}

    monkeypatch.setattr(helpers, "_load_json", _fake_load_json)
    # MCP prefetch is the partner showcase but must not be a second strategy.
    monkeypatch.setattr("src.core.mcp_client.load_preprocess_files_via_mcp",
                        lambda bid, names: {})

    data = AnalyzerAgent("b1").load_preprocess()

    # Every logical name resolved through the accessor (keys are the bare names).
    assert data["analysis"] == {"_via": "accessor", "file": "analysis.json"}
    assert data["meta"] == {"_via": "accessor", "file": "meta.json"}
    assert data["chapter_segments"] == {"_via": "accessor",
                                        "file": "chapter_segments.json"}
    assert "analysis.json" in seen and "chapter_segments.json" in seen


def test_heal_logic_has_exactly_one_caller(monkeypatch):
    """grep invariant: heal_if_local_fresher (the self-heal primitive) is INVOKED
    from exactly one place — the shared accessor in helpers.py. Any other module
    calling it would be a second strategy re-growing."""
    src_dir = pathlib.Path(helpers.__file__).resolve().parent.parent  # .../src
    call_sites: list[str] = []
    for py in src_dir.rglob("*.py"):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("def "):
                continue
            if re.search(r"\bheal_if_local_fresher\s*\(", line):
                call_sites.append(f"{py.name}:{i}")
    assert call_sites == [f"helpers.py:{_heal_call_line(helpers)}"], (
        f"heal called from {call_sites}; must be ONLY the helpers accessor"
    )


def _heal_call_line(helpers_mod) -> int:
    for i, line in enumerate(
        pathlib.Path(helpers_mod.__file__).read_text(encoding="utf-8").splitlines(), 1
    ):
        s = line.strip()
        if s.startswith("def ") or s.startswith("#"):
            continue
        if re.search(r"\bheal_if_local_fresher\s*\(", line):
            return i
    raise AssertionError("helpers no longer calls heal_if_local_fresher")
