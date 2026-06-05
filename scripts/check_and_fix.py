#!/usr/bin/env python3
"""Check and fix specific illustrations for character consistency.

Uses Gemini Vision to compare illustrations against character sheets,
and regenerates inconsistent pages with specific feedback.

Usage:
    # Check all pages
    python scripts/check_and_fix.py --book A_TALE_OF_TWO_CITIES

    # Check specific pages
    python scripts/check_and_fix.py --book A_TALE_OF_TWO_CITIES --pages 1,5,12

    # Check and auto-fix inconsistent pages
    python scripts/check_and_fix.py --book A_TALE_OF_TWO_CITIES --fix

    # Fix specific page
    python scripts/check_and_fix.py --book A_TALE_OF_TWO_CITIES --pages 5 --fix
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from src.config import GENERATED_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)


def _find_pages(book_id: str) -> list[dict]:
    """Find all generated page images."""
    pages_dir = GENERATED_DIR / book_id / "pages"
    if not pages_dir.exists():
        return []
    pages = []
    for f in sorted(pages_dir.glob("page_*.png")):
        # Skip retry versions (page_001_v1.png etc.)
        name = f.stem
        if "_v" in name:
            continue
        try:
            num = int(name.replace("page_", ""))
            pages.append({"page_number": num, "image_path": str(f)})
        except ValueError:
            continue
    return pages


def _find_sheets(book_id: str) -> list[dict]:
    """Find all character sheets."""
    ch_dir = GENERATED_DIR / book_id / "characters"
    if not ch_dir.exists():
        return []
    sheets = []
    for f in sorted(ch_dir.glob("*_sheet.*")):
        name = f.stem.replace("_sheet", "").replace("_", " ").title()
        sheets.append({
            "character_name": name,
            "sheet_path": str(f),
            "visual_identity": "",
        })
    return sheets


def check_pages(book_id: str, page_numbers: list[int] | None = None) -> list[dict]:
    """Check consistency of pages using Gemini Vision."""
    from src.generation.gemini_consistency_check import check_character_consistency

    pages = _find_pages(book_id)
    sheets = _find_sheets(book_id)

    if not pages:
        print("No pages found.")
        return []
    if not sheets:
        print("No character sheets found.")
        return []

    if page_numbers:
        pages = [p for p in pages if p["page_number"] in page_numbers]

    print(f"Checking {len(pages)} pages against {len(sheets)} character sheets...\n")

    results = []
    for page in pages:
        pn = page["page_number"]
        print(f"Page {pn:3d}: ", end="", flush=True)

        result = check_character_consistency(
            page["image_path"], sheets, page_num=pn,
        )

        if result["consistent"]:
            print(f"✓ consistent (score: {result['score']:.2f})")
        else:
            print(f"✗ INCONSISTENT (score: {result['score']:.2f})")
            for issue in result["issues"]:
                print(f"         - {issue}")

        results.append({"page_number": pn, **result})

    # Summary
    consistent_count = sum(1 for r in results if r["consistent"])
    print(f"\n=== Summary ===")
    print(f"  Consistent: {consistent_count}/{len(results)}")
    if consistent_count < len(results):
        bad_pages = [r["page_number"] for r in results if not r["consistent"]]
        print(f"  Needs fixing: pages {bad_pages}")
        print(f"  Run with --fix to auto-regenerate")

    return results


def fix_pages(book_id: str, check_results: list[dict]):
    """Regenerate inconsistent pages with Gemini feedback."""
    from src.generation.illustration import _get_client, _generate_single_page, _build_page_prompt

    inconsistent = [r for r in check_results if not r["consistent"]]
    if not inconsistent:
        print("All pages are consistent! Nothing to fix.")
        return

    sheets = _find_sheets(book_id)
    valid_sheets = [s for s in sheets if s.get("sheet_path") and Path(s["sheet_path"]).exists()]

    client = _get_client()
    output_dir = GENERATED_DIR / book_id / "pages"

    print(f"\nRegenerating {len(inconsistent)} inconsistent pages...\n")

    for result in inconsistent:
        pn = result["page_number"]
        feedback = result.get("feedback", "")

        print(f"Page {pn}: regenerating (feedback: {feedback[:80]})")

        save_path = output_dir / f"page_{pn:03d}"

        # Build page dict with feedback
        page = {
            "page_number": pn,
            "text": "",
            "scene_direction": "",
            "key_characters": [],
            "prompt": "",
        }

        # Try to load the original prompt from step logs
        steps_dir = GENERATED_DIR / book_id / "steps"
        prompts_file = steps_dir / "04_illustration_prompts.json"
        if prompts_file.exists():
            prompts_data = json.loads(prompts_file.read_text(encoding="utf-8"))
            for p in prompts_data.get("data", []):
                if p.get("page") == pn:
                    page["prompt"] = p.get("prompt", "")
                    break

        # Add consistency feedback to prompt
        extra = f"\n\nCRITICAL FIX REQUIRED:\n{feedback}" if feedback else ""
        original_prompt = _build_page_prompt(page, valid_sheets)
        page["prompt"] = original_prompt + extra

        success, image_path, _ = _generate_single_page(
            client, page, valid_sheets, save_path,
        )

        if success:
            print(f"  ✓ Regenerated: {image_path}")
        else:
            print(f"  ✗ Failed to regenerate")


def main():
    parser = argparse.ArgumentParser(description="Check and fix illustration consistency.")
    parser.add_argument("--book", required=True, help="Book ID")
    parser.add_argument("--pages", type=str, default=None, help="Comma-separated page numbers")
    parser.add_argument("--fix", action="store_true", help="Auto-regenerate inconsistent pages")
    args = parser.parse_args()

    page_numbers = None
    if args.pages:
        page_numbers = [int(p.strip()) for p in args.pages.split(",")]

    results = check_pages(args.book, page_numbers)

    if args.fix and results:
        fix_pages(args.book, results)


if __name__ == "__main__":
    main()
