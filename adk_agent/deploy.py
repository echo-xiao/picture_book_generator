"""Deploy the StorySprout ADK agent to Vertex AI Agent Engine.

Agent Engine is Agent Builder's managed runtime. The sandbox is pure Python (no
Node), so the deployed agent uses the direct-pymongo tool (ADK_MONGO_MODE=pymongo);
the literal MongoDB MCP-server integration runs in the local / Cloud Run path.

Gemini 3.5 Flash is only served on the `global` endpoint, so even though the
engine resource lives in a region, the agent's model calls are pointed at
`global` via GOOGLE_CLOUD_LOCATION in env_vars.

Usage:
    PYTHONPATH=. python adk_agent/deploy.py
"""

from __future__ import annotations

import os

import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

PROJECT = os.getenv("GCP_PROJECT", "picture-book-gen")
LOCATION = os.getenv("AGENT_ENGINE_LOCATION", "us-central1")
STAGING_BUCKET = os.getenv("STAGING_BUCKET", f"gs://{PROJECT}-agent-engine")

try:
    from src.config import MONGODB_URI, MONGODB_DB
except Exception:  # pragma: no cover
    MONGODB_URI = os.environ["MONGODB_URI"]
    MONGODB_DB = os.environ.get("MONGODB_DB", "picture_book_generator")

# Build the agent graph in pymongo mode (no Node in Agent Engine).
os.environ["ADK_MONGO_MODE"] = "pymongo"
from adk_agent.agent import root_agent  # noqa: E402

vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING_BUCKET)

app = AdkApp(agent=root_agent)

print(f"Deploying '{root_agent.name}' to Agent Engine in {LOCATION} ...")
print("(this builds a container remotely and can take several minutes)")

remote = agent_engines.create(
    agent_engine=app,
    display_name="StorySprout Book Agent (ADK)",
    description=(
        "Analyzer -> Writer -> Art Director pipeline. Reasoning on Gemini 3.5 Flash "
        "(Vertex AI / Agent Platform); character data from MongoDB Atlas."
    ),
    requirements=[
        "google-adk",
        "google-cloud-aiplatform[adk,agent_engines]",
        "pymongo",
    ],
    extra_packages=["adk_agent"],
    env_vars={
        "GOOGLE_CLOUD_LOCATION": "global",  # Gemini 3.5 Flash is global-only
        "ADK_MONGO_MODE": "pymongo",
        "ADK_MODEL": "gemini-3.5-flash",
        "MONGODB_URI": MONGODB_URI,
        "MONGODB_DB": MONGODB_DB,
    },
)

print("\nDEPLOYED OK")
print("resource_name:", remote.resource_name)
