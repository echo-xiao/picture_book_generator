"""Root cause B: the chapter subprocess shares the web read path's freshness
heal, so both resolve to the same MongoDB-authoritative version.

_save_json dual-writes Mongo + file best-effort. A Mongo write that fails
during an editor save leaves the doc stale but the file fresh. The web read
(_load_json) heals toward the newer file and repairs the doc; the subprocess
read (analyzer.load_preprocess) did NOT, so whole-chapter generation read the
stale doc — the editor and the generator saw different versions of the book.

Fix = one shared heal: load_preprocess applies the same freshness override,
keeping MongoDB the authority (the heal repairs the doc).
"""

from __future__ import annotations

import json

import pytest

import src.routes.helpers as helpers
from src.agents.analyzer import AnalyzerAgent


@pytest.fixture()
def stale_mongo(monkeypatch, tmp_path):
    monkeypatch.setattr("src.agents.analyzer.GENERATED_DIR", tmp_path)
    monkeypatch.setattr(helpers, "GENERATED_DIR", tmp_path)

    # Local file = the FRESH, just-edited version (real file, current mtime).
    pre = tmp_path / "b1" / "preprocess"
    pre.mkdir(parents=True)
    fresh = {"segments": [{"id": 0, "simplified_text": "NEW edited text"}]}
    (pre / "analysis.json").write_text(json.dumps(fresh))

    # MCP unavailable in tests.
    monkeypatch.setattr("src.core.mcp_client.load_preprocess_files_via_mcp",
                        lambda bid, names: {})
    # pymongo path: the doc is STALE (the failed-write scenario), stamped far
    # in the past so the real file mtime is unambiguously newer.
    stale = {"segments": [{"id": 0, "simplified_text": "OLD stale text"}]}
    monkeypatch.setattr("src.core.db.is_available", lambda: True)
    monkeypatch.setattr("src.core.db.load_preprocess_file",
                        lambda bid, fn: stale if fn == "analysis.json" else None)
    monkeypatch.setattr("src.core.db.load_preprocess_file_with_meta",
                        lambda bid, fn: (stale, "2000-01-01T00:00:00+00:00")
                        if fn == "analysis.json" else None)
    healed = {}
    monkeypatch.setattr("src.core.db.save_preprocess_file",
                        lambda bid, fn, data: healed.__setitem__(fn, data) or True)
    return {"fresh": fresh, "healed": healed}


def test_subprocess_read_honours_fresher_file(stale_mongo):
    data = AnalyzerAgent("b1").load_preprocess()
    assert data["analysis"]["segments"][0]["simplified_text"] == "NEW edited text"


def test_subprocess_read_repairs_the_stale_doc(stale_mongo):
    AnalyzerAgent("b1").load_preprocess()
    # MongoDB stays the authority: the stale doc is healed from the file.
    assert stale_mongo["healed"].get("analysis.json", {}) == stale_mongo["fresh"]
