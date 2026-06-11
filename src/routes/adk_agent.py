"""'AI Agent' route — runs the StorySprout ADK agent on Vertex AI Agent Engine.

The website's AI Agent panel POSTs here. The request is forwarded to the ADK
`SequentialAgent` (Analyzer -> Writer -> Art Director) deployed on Vertex AI
Agent Engine (Agent Builder's managed runtime). That agent reads character data
from MongoDB Atlas and reasons with Gemini 3.5 Flash on Vertex AI, returning a
kid-friendly illustrated-page plan.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from src.config import AGENT_ENGINE_RESOURCE, GCP_PROJECT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/adk", tags=["adk-agent"])


class PlanRequest(BaseModel):
    book_id: str
    chapter_text: str


def _run_on_agent_engine(book_id: str, chapter_text: str) -> dict:
    """Stream the deployed Agent Engine agent and collect each stage's output."""
    import vertexai
    from vertexai import agent_engines

    # The engine is regional (us-central1); its Gemini calls target the global
    # endpoint via env_vars set at deploy time.
    vertexai.init(project=GCP_PROJECT, location="us-central1")
    remote = agent_engines.get(AGENT_ENGINE_RESOURCE)

    message = f"book_id: {book_id}\n\nChapter text:\n{chapter_text}"
    by_author: dict[str, str] = {}
    tool_calls: list[str] = []
    for event in remote.stream_query(user_id="web", message=message):
        ev = event if isinstance(event, dict) else {}
        author = ev.get("author", "?")
        for part in ((ev.get("content") or {}).get("parts") or []):
            fc = part.get("function_call")
            if fc:
                tool_calls.append(f"{author}:{fc.get('name')}")
            if part.get("text"):
                by_author[author] = part["text"]

    return {
        "character_brief": by_author.get("analyzer", ""),
        "pages": by_author.get("writer", ""),
        "illustration_prompts": by_author.get("art_director", ""),
        "tool_calls": tool_calls,
        "runtime": "Vertex AI Agent Engine",
        "model": "gemini-3.5-flash (Vertex AI)",
    }


@router.post("/plan")
async def adk_plan(req: PlanRequest):
    """Run the ADK book-planning agent (on Agent Engine) for one chapter.

    Note: Agent Engine scales to zero, so the first call after idle may take up
    to ~1 minute to warm up.
    """
    try:
        return await run_in_threadpool(_run_on_agent_engine, req.book_id, req.chapter_text)
    except Exception as e:  # surface a clean message to the UI
        logger.exception("ADK agent plan failed")
        return {
            "error": str(e)[:400],
            "character_brief": "",
            "pages": "",
            "illustration_prompts": "",
            "tool_calls": [],
        }
