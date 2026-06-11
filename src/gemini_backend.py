"""Centralized Gemini client factory.

Every Gemini call in the project (text + image + QA checks) builds its client
through `make_genai_client()`, so the backend is switched in exactly one place.

Backends (GEMINI_BACKEND):
  - "vertex"  -> Vertex AI / "Agent Platform" (Gemini models on Agent Platform).
                 Auth comes from ADC locally or the attached service account on
                 Cloud Run; billing goes to GCP_PROJECT. This is the default and
                 the path required by the hackathon ("Gemini models on Agent
                 Platform").
  - "api_key" -> Google AI Studio key endpoint (GEMINI_API_KEY).
"""

from __future__ import annotations

import logging

from src.config import (
    GCP_LOCATION,
    GCP_PROJECT,
    GEMINI_API_KEY,
    GEMINI_BACKEND,
)

logger = logging.getLogger(__name__)


def make_genai_client():
    """Return a configured google-genai Client for the active backend."""
    from google import genai

    if GEMINI_BACKEND == "vertex":
        if not GCP_PROJECT:
            raise ValueError(
                "GEMINI_BACKEND=vertex but no GCP project is set "
                "(set GCP_PROJECT or GOOGLE_CLOUD_PROJECT)."
            )
        logger.debug("Gemini backend: Vertex AI (project=%s, location=%s)", GCP_PROJECT, GCP_LOCATION)
        return genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_BACKEND=api_key but GEMINI_API_KEY is not set.")
    logger.debug("Gemini backend: AI Studio API key")
    return genai.Client(api_key=GEMINI_API_KEY)
