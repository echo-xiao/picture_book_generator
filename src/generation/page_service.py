"""Shared single-page QA + bounded self-correction policy.

ONE place for the rule "QA-check a freshly generated page; if it scores below
threshold, regenerate it once with the QA feedback and keep whichever image
scores higher" — plus the threshold itself. Both the ADK pipeline (Artist) and
the single-page regen endpoint use this so they can't drift (the threshold was
previously hard-coded as 50 in two backends and 75 in the frontend, with 1 vs 3
retries). The frontend now only *triggers* regeneration; it no longer runs its
own retry loop.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

# Single source of truth for the self-correction policy.
SELF_CORRECT_THRESHOLD = 50
MAX_SELF_CORRECT_RETRIES = 1


def qa_and_self_correct(
    *,
    image_path: str,
    character_sheets: list,
    expected_text: str,
    expected_characters: list,
    page_num: int,
    history_dir: Path,
    quality_path: Path,
    regenerate_fn: Callable[[str], str],
    seg_id=None,
    self_correct: bool = True,
    threshold: int = SELF_CORRECT_THRESHOLD,
) -> dict:
    """QA `image_path`; if below `threshold`, regenerate once and keep the better.

    `regenerate_fn(feedback) -> new_image_path` performs the actual regeneration
    in place (returning the new path, or "" on failure). The old image is moved
    to `history_dir` first so the generator's on-disk checkpoint doesn't skip it;
    if the retry scores worse it is restored. The (possibly updated) quality
    report is written to `quality_path` and returned.
    """
    from src.generation.gemini_consistency_check import check_page_quality

    def _qa(path: str) -> dict:
        res = check_page_quality(path, character_sheets, expected_text, expected_characters, page_num)
        res["page"] = page_num
        if seg_id is not None:
            res["segment_id"] = seg_id
        return res

    result = _qa(image_path)
    if (
        self_correct
        and result.get("overall_score", 100) < threshold
        and result.get("regeneration_feedback")
    ):
        old_score = result["overall_score"]
        feedback = result["regeneration_feedback"]
        bad = Path(image_path)
        history_dir.mkdir(parents=True, exist_ok=True)
        backup = history_dir / f"{bad.stem}_selfcorrect_prev{bad.suffix}"
        shutil.move(str(bad), str(backup))
        new_path = regenerate_fn(feedback) or ""
        if not new_path:
            shutil.copy2(str(backup), str(bad))
            result["self_correct_attempted"] = True
        else:
            new_result = _qa(new_path)
            # If QA itself failed on the retry, its score is a sentinel 100 — don't
            # trust it; keep the original rather than risk swapping in a worse image.
            new_score = -1 if new_result.get("qa_failed") else new_result.get("overall_score", 0)
            kept_new = new_score >= old_score
            if not kept_new:
                Path(new_path).unlink(missing_ok=True)
                shutil.copy2(str(backup), str(bad))
            result = new_result if kept_new else result
            result["self_correct_attempted"] = True
            result["self_correct"] = {
                "old_score": old_score, "new_score": new_score,
                "kept": "new" if kept_new else "old",
            }

    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        json.dumps(result, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
    )
    return result
