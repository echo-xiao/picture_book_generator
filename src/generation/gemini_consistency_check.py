"""Gemini Vision-based character consistency check.

Sends the generated illustration + character sheet to Gemini and asks
it to verify if the characters match. If not, returns specific feedback
about what's wrong (e.g., "missing glasses", "wrong hair color").
"""

import base64
import logging
from pathlib import Path

from google import genai

from src.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _load_image_part(image_path: str) -> dict | None:
    path = Path(image_path)
    if not path.exists():
        return None
    try:
        data = path.read_bytes()
        suffix = path.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        return {
            "inline_data": {
                "mime_type": mime,
                "data": base64.b64encode(data).decode("utf-8"),
            }
        }
    except Exception as e:
        logger.warning("Failed to load image %s: %s", image_path, e)
        return None


def check_character_consistency(
    illustration_path: str,
    character_sheets: list[dict],
    page_num: int = 0,
) -> dict:
    """Check if characters in an illustration match their reference sheets.

    Args:
        illustration_path: Path to the generated page illustration.
        character_sheets: List of character sheet dicts with 'character_name',
                         'sheet_path', and 'visual_identity'.
        page_num: Page number for logging.

    Returns:
        dict with:
            - consistent: bool (True if all characters match)
            - score: float (0-1, overall consistency)
            - issues: list of str (specific problems found)
            - feedback: str (combined feedback for regeneration prompt)
    """
    client = _get_client()

    # Build multi-part content: illustration + character sheets
    parts = []

    # Add the illustration
    parts.append({"text": "[PAGE ILLUSTRATION to check]"})
    ill_part = _load_image_part(illustration_path)
    if not ill_part:
        return {"consistent": True, "score": 1.0, "issues": [], "feedback": ""}
    parts.append(ill_part)

    # Add character sheets as references
    sheets_added = 0
    char_names = []
    for sheet in character_sheets:
        sheet_path = sheet.get("sheet_path", "")
        if not sheet_path:
            continue
        img_part = _load_image_part(sheet_path)
        if img_part:
            name = sheet.get("character_name", "character")
            vi = sheet.get("visual_identity", "")
            parts.append({"text": f"[REFERENCE SHEET for {name}]: {vi}"})
            parts.append(img_part)
            char_names.append(name)
            sheets_added += 1
            if sheets_added >= 5:
                break

    if sheets_added == 0:
        return {"consistent": True, "score": 1.0, "issues": [], "feedback": ""}

    # Ask Gemini to compare
    parts.append({"text": f"""Compare the PAGE ILLUSTRATION with the CHARACTER REFERENCE SHEETS above.

Characters to check: {', '.join(char_names)}

For EACH character visible in the illustration, check:
1. Hair color and style — does it match the reference sheet?
2. Clothing/outfit — same colors and style as reference?
3. Distinctive features — glasses, freckles, accessories present?
4. Overall appearance — would a child recognize this as the same person?

Return JSON:
{{
  "overall_consistent": true/false,
  "score": 0.0 to 1.0 (1.0 = perfect match),
  "characters_checked": [
    {{
      "name": "character name",
      "found_in_illustration": true/false,
      "consistent": true/false,
      "issues": ["list of specific mismatches, e.g., 'missing glasses', 'hair should be brown not blonde'"]
    }}
  ],
  "regeneration_feedback": "If inconsistent, describe exactly what needs to be fixed in the next generation attempt"
}}"""})

    try:
        from src.agent.gemini_client import generate_json
        # We need to call with multipart content, so use the client directly
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=parts,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        import json
        result = json.loads(response.text)

        consistent = result.get("overall_consistent", True)
        score = result.get("score", 1.0)
        chars = result.get("characters_checked", [])
        issues = []
        for c in chars:
            if not c.get("consistent", True):
                for issue in c.get("issues", []):
                    issues.append(f"{c.get('name', '?')}: {issue}")

        feedback = result.get("regeneration_feedback", "")

        logger.info(
            "Page %d Gemini consistency: score=%.2f, consistent=%s, issues=%d",
            page_num, score, consistent, len(issues),
        )
        if issues:
            for issue in issues:
                logger.info("  Issue: %s", issue)

        return {
            "consistent": consistent,
            "score": score,
            "issues": issues,
            "feedback": feedback,
        }

    except Exception as e:
        logger.warning("Gemini consistency check failed: %s", e)
        return {"consistent": True, "score": 1.0, "issues": [], "feedback": ""}
