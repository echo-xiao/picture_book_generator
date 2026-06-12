"""chapter_data.json stays in step after single-page changes (H5).

High-risk review finding: chapter_data.json (the combined PDF's source)
stored the absolute image path + text from generation time. A single-page
regen that switched extensions (.png → .jpg) left a dead path — a silently
blank page in the next book.pdf — and edited/restored text never reached it.
"""

from __future__ import annotations

import json

import pytest

from src.routes.helpers import update_chapter_data_page
from tests.conftest import make_segment


@pytest.fixture()
def chapter_data(monkeypatch, tmp_path):
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)
    ch = tmp_path / "somebook" / "chapters" / "ch00"
    ch.mkdir(parents=True)
    path = ch / "chapter_data.json"
    path.write_text(json.dumps({
        "chapter_idx": 0, "chapter_title": "Ch 1",
        "pages": [
            {"text": "old text", "image_path": "/app/data/ch00/pages/page_001.png", "page_number": 1},
            {"text": "page two", "image_path": "/app/data/ch00/pages/page_002.png", "page_number": 2},
        ],
    }))
    return path


def _pages(path):
    return json.loads(path.read_text())["pages"]


def test_updates_image_path_and_text(chapter_data):
    update_chapter_data_page("somebook", 0, 1,
                             image_path="/app/data/ch00/pages/page_001.jpg",
                             text="new text")
    pages = _pages(chapter_data)
    assert pages[0]["image_path"].endswith("page_001.jpg")
    assert pages[0]["text"] == "new text"
    assert pages[1]["text"] == "page two", "other pages untouched"


def test_text_only_update_keeps_image(chapter_data):
    update_chapter_data_page("somebook", 0, 2, text="edited")
    pages = _pages(chapter_data)
    assert pages[1]["text"] == "edited"
    assert pages[1]["image_path"].endswith("page_002.png")


def test_legacy_entry_matched_via_filename(chapter_data):
    data = json.loads(chapter_data.read_text())
    for p in data["pages"]:
        del p["page_number"]  # pre-page_number schema
    chapter_data.write_text(json.dumps(data))

    update_chapter_data_page("somebook", 0, 2, text="legacy edited")
    assert _pages(chapter_data)[1]["text"] == "legacy edited"


def test_noop_when_chapter_never_generated(monkeypatch, tmp_path):
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)
    update_chapter_data_page("somebook", 0, 1, text="x")  # must not raise


def test_restore_version_updates_chapter_data(client, monkeypatch, tmp_path):
    """End-to-end: restoring a .jpg version over a .png current must repoint
    chapter_data.json at the restored file."""
    analysis = {"segments": [make_segment(0)]}
    monkeypatch.setattr(
        "src.routes.editor._load_json",
        lambda book_id, filename: analysis if filename == "analysis.json" else {},
    )
    monkeypatch.setattr("src.routes.editor.GENERATED_DIR", tmp_path)
    monkeypatch.setattr("src.routes.helpers.GENERATED_DIR", tmp_path)

    ch = tmp_path / "somebook" / "chapters" / "ch00"
    (ch / "pages").mkdir(parents=True)
    (ch / "history").mkdir()
    (ch / "pages" / "page_001.png").write_bytes(b"CURRENT")
    (ch / "history" / "page_001_1000.jpg").write_bytes(b"OLD")
    (ch / "chapter_data.json").write_text(json.dumps({
        "pages": [{"text": "t", "image_path": str(ch / "pages" / "page_001.png"), "page_number": 1}],
    }))

    resp = client.post("/api/book/somebook/segment/0/restore-version?version=1000")
    assert resp.status_code == 200
    pages = json.loads((ch / "chapter_data.json").read_text())["pages"]
    assert pages[0]["image_path"].endswith("page_001.jpg")
