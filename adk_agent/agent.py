"""StorySprout book-planning agent — built with Google's Agent Development Kit (ADK).

A deterministic SequentialAgent (Analyzer -> Writer -> Art Director) that turns a
source-book chapter into a kid-friendly, illustrated-page plan.

All three hackathon pillars live in this one agent:
  * Gemini 3.5 Flash on Vertex AI ("Agent Platform")  -> reasoning for every stage
  * MongoDB's official MCP server, attached as a tool  -> reads character /
                                                          consistency data from Atlas
  * ADK SequentialAgent                                -> fixed-order orchestration

The agent is intentionally self-contained (it does not import the heavy media
pipeline) so it stays light enough to deploy to Vertex AI Agent Engine.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent, SequentialAgent

# Config: prefer the project's settings; fall back to env vars when this package
# is shipped on its own (e.g. packaged for Agent Engine).
try:
    from src.config import MONGODB_URI, MONGODB_DB
except Exception:  # pragma: no cover - packaged outside the repo
    MONGODB_URI = os.environ.get("MDB_MCP_CONNECTION_STRING") or os.environ.get("MONGODB_URI", "")
    MONGODB_DB = os.environ.get("MONGODB_DB", "picture_book_generator")

MODEL = os.getenv("ADK_MODEL", "gemini-3.5-flash")


def _mongo_toolset():
    """Expose the official MongoDB MCP server to the agent as read-only tools.

    Imports are local so the Node-less pymongo path (Agent Engine) does not need
    the `mcp` package. The full environment is forwarded so `npx`/Node resolve on
    PATH; the Atlas connection string is injected like src/core/mcp_client.py.
    """
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    from mcp import StdioServerParameters

    env = {**os.environ, "MDB_MCP_CONNECTION_STRING": MONGODB_URI}
    return McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server", "--readOnly"],
            env=env,
        ),
        tool_filter=["find"],
    )


def _find_characters(book_id: str) -> list:
    """Direct-pymongo equivalent of the MCP find, for runtimes without Node
    (e.g. Vertex AI Agent Engine, which is pure Python and cannot launch npx).

    Returns up to 8 lead-cast (role 'main'/'supporting') character documents.
    """
    import pymongo

    client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)
    try:
        db = client[MONGODB_DB]
        return list(
            db.characters.find(
                {"book_id": book_id, "role": {"$in": ["main", "supporting"]}},
                {"_id": 0, "canonical_name": 1, "role": 1, "appearance": 1, "visual_details": 1},
            ).limit(8)
        )
    finally:
        client.close()


# ADK_MONGO_MODE selects how the agent reaches MongoDB:
#   "mcp"     -> the official MongoDB MCP server over stdio (npx). Default; used
#                locally and on Cloud Run; this is the literal partner MCP integration.
#   "pymongo" -> a direct-pymongo FunctionTool, for the Node-less Agent Engine runtime.
MONGO_MODE = os.getenv("ADK_MONGO_MODE", "mcp").lower()


def _analyzer_tools():
    if MONGO_MODE == "pymongo":
        from google.adk.tools import FunctionTool
        return [FunctionTool(_find_characters)]
    return [_mongo_toolset()]


analyzer = LlmAgent(
    name="analyzer",
    model=MODEL,
    description="Reads the cast of a book from MongoDB and summarises who matters.",
    instruction=(
        "You are the Analyzer in a picture-book pipeline. "
        f"You can query the MongoDB database '{MONGODB_DB}' through one tool. "
        "The 'characters' collection has fields: book_id, canonical_name, role, gender, "
        "description, appearance, visual_details. The 'role' value is one of 'main', "
        "'supporting', or 'minor'. "
        "The user message contains a book_id. Use your tool exactly once to fetch the lead "
        "cast for that book_id — the characters whose role is 'main' or 'supporting' "
        "(limit to 8 documents). Call the tool only once. After the results come back, "
        "STOP using tools and write a SHORT cast brief: one line per character as "
        "'Name - role - key visual traits', focusing on appearance and visual_details. "
        "Max 8 lines. If nothing is found, write 'No main characters found.'"
    ),
    tools=_analyzer_tools(),
    output_key="character_brief",
)

writer = LlmAgent(
    name="writer",
    model=MODEL,
    description="Rewrites a chapter into simple picture-book pages for ages 4-6.",
    instruction=(
        "You are the Writer for a children's picture book (ages 4-6).\n"
        "Cast brief from the Analyzer:\n{character_brief}\n\n"
        "Using the chapter text in the user message, rewrite it into 4-6 short pages. "
        "Each page is 1-2 simple sentences a young child understands, stays faithful to "
        "the story, and is gentle with no scary content. "
        "Output a numbered list, one line each: 'Page N: <text>'."
    ),
    output_key="pages",
)

art_director = LlmAgent(
    name="art_director",
    model=MODEL,
    description="Writes per-page illustration prompts with consistent character looks.",
    instruction=(
        "You are the Art Director.\n"
        "Cast brief:\n{character_brief}\n\n"
        "Pages:\n{pages}\n\n"
        "For each page write ONE warm, child-friendly illustration prompt. Name which "
        "characters appear and restate their key visual traits from the cast brief so "
        "their look stays consistent across every page. "
        "Output a numbered list, one line each: 'Page N: <illustration prompt>'."
    ),
    output_key="illustration_prompts",
)

# `root_agent` is the conventional ADK entry point (used by `adk run`, the dev UI,
# and Agent Engine deployment).
root_agent = SequentialAgent(
    name="storysprout_book_agent",
    description=(
        "Turns a source-book chapter into a kid-friendly illustrated-page plan "
        "(Analyzer -> Writer -> Art Director). Reasoning runs on Gemini 3.5 Flash via "
        "Vertex AI; character data is read from MongoDB Atlas through the official "
        "MongoDB MCP server."
    ),
    sub_agents=[analyzer, writer, art_director],
)
