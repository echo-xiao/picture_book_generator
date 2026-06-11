"""Run the StorySprout ADK agent locally against a real book chapter.

Usage:
    PYTHONPATH=. python adk_agent/run_local.py [book_id]

Requires Application Default Credentials (gcloud auth application-default login)
and the Vertex AI / Agent Platform API enabled on the project.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Gemini on Vertex AI / "Agent Platform" (the model-side requirement).
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "picture-book-gen"))
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_LOCATION", "global"))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from adk_agent.agent import root_agent

# A short, self-contained chapter excerpt (The Great Gatsby, Ch.1).
CHAPTER_TEXT = (
    "Nick Carraway moved to a small house in West Egg, next door to a huge mansion. "
    "One evening he drove over to East Egg to have dinner with his cousin Daisy "
    "Buchanan and her husband Tom. Daisy's friend Jordan Baker was there too, lying "
    "on the couch. Across the bay, a mysterious man named Gatsby stood alone on his "
    "lawn, reaching out toward a single green light at the end of Daisy's dock."
)


async def main(book_id: str) -> None:
    app_name, user_id = "storysprout", "demo"
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=app_name, user_id=user_id)
    runner = Runner(agent=root_agent, app_name=app_name, session_service=session_service)

    prompt = f"book_id: {book_id}\n\nChapter text:\n{CHAPTER_TEXT}"
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    tool_calls: list[str] = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=message
    ):
        parts = (event.content.parts if event.content else None) or []
        for part in parts:
            fc = getattr(part, "function_call", None)
            if fc is not None:
                tool_calls.append(f"{event.author}:{fc.name}")
                print(f"[tool-call] {event.author} -> {fc.name}", flush=True)
            if getattr(part, "function_response", None) is not None:
                print(f"[tool-resp] {event.author} <- (data received)", flush=True)
        if event.is_final_response() and event.content and event.content.parts:
            preview = (event.content.parts[0].text or "")[:100].replace("\n", " ")
            print(f"[stage-done] {event.author}: {preview}...", flush=True)

    final = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session.id
    )
    state = final.state
    print("\nMCP TOOL CALLS ->", tool_calls or "(none)")
    print("\n========== 1) CHARACTER BRIEF (Analyzer + MongoDB MCP) ==========")
    print(state.get("character_brief", "(missing)"))
    print("\n========== 2) PAGES (Writer) ==========")
    print(state.get("pages", "(missing)"))
    print("\n========== 3) ILLUSTRATION PROMPTS (Art Director) ==========")
    print(state.get("illustration_prompts", "(missing)"))


if __name__ == "__main__":
    book = sys.argv[1] if len(sys.argv) > 1 else "the_great_gatsby"
    asyncio.run(main(book))
