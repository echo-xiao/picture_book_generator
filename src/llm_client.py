"""Unified LLM client for text tasks. Gemini-only.

Usage:
    from src.llm_client import generate_json

    result = generate_json("Analyze this text...", system="You are a literary analyst.")
"""

import json
import logging
from typing import Any

from src.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BACKEND

logger = logging.getLogger(__name__)


def _call_gemini(prompt: str, system: str = "", max_retries: int = 3) -> str:
    """Call Gemini API."""
    from google import genai
    from src.gemini_backend import make_genai_client

    client = make_genai_client()
    config = genai.types.GenerateContentConfig(
        response_mime_type="application/json",
    )
    if system:
        config.system_instruction = system

    from src.gemini_backend import call_gemini_with_backoff

    def _attempt() -> str:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        if response.text is None:
            raise ValueError("Gemini returned empty response (blocked or truncated)")
        return response.text

    # Single shared retry policy (rate-limit/transient backoff, free-tier fast-fail).
    return call_gemini_with_backoff(_attempt, max_retries=max_retries, base=2.0, label="text")


def generate_json(prompt: str, system: str = "", max_retries: int = 3) -> dict[str, Any]:
    """Generate JSON from Gemini.

    Args:
        prompt: The user prompt.
        system: Optional system instruction.
        max_retries: Max retry attempts.

    Returns:
        Parsed JSON dict.
    """
    if GEMINI_BACKEND != "vertex" and not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set (and GEMINI_BACKEND is not 'vertex').")
    raw = _call_gemini(prompt, system, max_retries)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to fix common JSON issues
    import re

    # Extract from markdown code blocks
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Fix trailing commas: ,} → } and ,] → ]
    fixed = re.sub(r',\s*([}\]])', r'\1', raw)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Fix unescaped quotes in strings by trying to find the JSON object
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
        fixed2 = re.sub(r',\s*([}\]])', r'\1', match.group(0))
        try:
            return json.loads(fixed2)
        except json.JSONDecodeError:
            pass

    logger.error("Failed to parse JSON. Raw response: %s", raw[:1000])
    raise ValueError("LLM returned invalid JSON")
