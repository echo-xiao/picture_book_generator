"""PDF export for picture books using reportlab."""

import logging
import os
from pathlib import Path

from reportlab.lib.pagesizes import inch
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# 8.5" x 8.5" square picture book
PAGE_SIZE = (8.5 * inch, 8.5 * inch)


def _register_fonts() -> str:
    try:
        pdfmetrics.registerFont(TTFont("ComicSans", "Comic Sans MS.ttf"))
        return "ComicSans"
    except Exception:
        pass
    return "Helvetica"


def _draw_full_image_page(c: canvas.Canvas, image_path: str, width: float, height: float) -> bool:
    """Draw a full-page image. Returns True if successful."""
    if not image_path or not os.path.exists(image_path):
        return False
    try:
        c.drawImage(
            image_path, 0, 0,
            width=width, height=height,
            preserveAspectRatio=True, anchor="c",
        )
        c.showPage()
        return True
    except Exception as e:
        logger.warning("Could not draw image %s: %s", image_path, e)
        return False


def _find_image(directory: str | Path, name: str) -> str:
    """Find an image file by name (trying .png and .jpg)."""
    d = Path(directory)
    for ext in (".png", ".jpg"):
        candidate = d / f"{name}{ext}"
        if candidate.exists():
            return str(candidate)
    return ""


def export_pdf(
    pages: list[dict],
    book_title: str,
    output_path: str,
    cover_image: str = "",
    special_dir: str = "",
    chapter_num: int | None = None,
) -> str:
    """Export the picture book as a PDF.

    Pages with images use the image as full-page (text is already embedded
    by Gemini in the illustration). No additional text overlay.

    Special pages (cover, chapter cover, chapter ending, back cover) are
    inserted from the special_dir if available.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Auto-detect special_dir if not provided
    if not special_dir:
        special_dir = str(output.parent / "special")

    width, height = PAGE_SIZE
    font = _register_fonts()

    c = canvas.Canvas(str(output), pagesize=PAGE_SIZE)
    c.setTitle(book_title)
    c.setAuthor("Picture Book Generator")

    special = Path(special_dir)

    # 1. Book cover (full image, no text overlay)
    book_cover = cover_image or _find_image(special, "book_cover")
    if book_cover:
        _draw_full_image_page(c, book_cover, width, height)

    # 2. Chapter cover (if available)
    if chapter_num is not None:
        ch_cover = _find_image(special, f"chapter_{chapter_num:02d}_cover")
        if ch_cover:
            _draw_full_image_page(c, ch_cover, width, height)

    # 3. Content pages — image fills entire page, no text overlay
    for idx, page in enumerate(pages):
        image_path = page.get("image_path", "")
        if image_path and os.path.exists(image_path):
            _draw_full_image_page(c, image_path, width, height)
        else:
            # Fallback: text-only page
            text = page.get("text", "")
            if text:
                bg = HexColor("#fffaf4")
                c.setFillColor(bg)
                c.rect(0, 0, width, height, fill=1, stroke=0)
                c.setFillColor(HexColor("#3d3229"))
                c.setFont(font, 18)
                import textwrap
                max_chars = int((width - 1.2 * inch) / (18 * 0.5))
                lines = textwrap.wrap(text, width=max_chars)
                y = height * 0.7
                for line in lines:
                    if y < inch:
                        break
                    c.drawString(0.6 * inch, y, line)
                    y -= 18 * 1.6
                c.showPage()

    # 4. Chapter ending (if available)
    if chapter_num is not None:
        ch_ending = _find_image(special, f"chapter_{chapter_num:02d}_ending")
        if ch_ending:
            _draw_full_image_page(c, ch_ending, width, height)

    # 5. Back cover
    back_cover = _find_image(special, "back_cover")
    if back_cover:
        _draw_full_image_page(c, back_cover, width, height)

    c.save()
    abs_path = str(output.resolve())
    logger.info("PDF exported to %s", abs_path)
    return abs_path
