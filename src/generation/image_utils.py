"""Shared image utilities for Gemini-based generation modules."""

import base64
import logging
from pathlib import Path

from google import genai

from src.gemini_backend import make_genai_client

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = make_genai_client()
    return _client


def _load_image_part(image_path: str) -> dict | None:
    """Load an image file and return a Gemini-compatible Part dict."""
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
        logger.warning("Failed to load reference image %s: %s", image_path, e)
        return None
