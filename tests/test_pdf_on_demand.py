"""Root cause III: book.pdf is built on demand, never a stale stored artifact.

GET /api/book/{id}/pdf derives the PDF from chapter_data + special pages (the
single source the editors maintain) per request, so it can't go stale and needs
no cross-endpoint sync. 404 when nothing is generated yet.
"""

from __future__ import annotations

import json

import src.routes.books as books


def test_pdf_404_when_no_chapters(client, monkeypatch, tmp_path):
    monkeypatch.setattr(books, "GENERATED_DIR", tmp_path)
    assert client.get("/api/book/emptybook/pdf").status_code == 404


def test_pdf_built_from_chapter_data_on_demand(client, monkeypatch, tmp_path):
    monkeypatch.setattr(books, "GENERATED_DIR", tmp_path)
    monkeypatch.setattr(books, "_load_json", lambda bid, fn: {"title": "My Book"})

    # Two chapters, out of order on disk — must be combined in chapter order
    # with each page tagged by chapter.
    for idx, name in ((1, "ch01"), (0, "ch00")):
        d = tmp_path / "b" / "chapters" / name
        d.mkdir(parents=True)
        (d / "chapter_data.json").write_text(json.dumps({
            "chapter_idx": idx,
            "pages": [{"page_number": 1, "image_path": "", "text": f"chapter {idx} page"}],
        }))

    captured = {}

    def _fake_export(pages, title, out_path, special_dir=""):
        captured["pages"] = pages
        captured["title"] = title
        with open(out_path, "wb") as f:
            f.write(b"%PDF-1.4 fake")
        return out_path

    monkeypatch.setattr("src.renderer.pdf_export.export_pdf", _fake_export)

    resp = client.get("/api/book/b/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert captured["title"] == "My Book"
    # Combined in chapter order, each page tagged with its 1-based chapter.
    nums = [p["_chapter_num"] for p in captured["pages"]]
    assert nums == [1, 2]
