"""FastAPI application for the picture-book generator."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import GENERATED_DIR
from src.routes import books, editor, generation

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Picture Book Generator",
    version="0.1.0",
    description="Generate illustrated children's picture books from text.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timeout middleware — prevent hung requests from blocking the server
class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=120)
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Request timed out"}, status_code=504)


app.add_middleware(TimeoutMiddleware)

# Serve generated images / assets
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(GENERATED_DIR)), name="static")

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(books.router)
app.include_router(editor.router)
app.include_router(generation.router)

# ---------------------------------------------------------------------------
# Mount frontend (SPA) -- must be last so API routes take priority
# ---------------------------------------------------------------------------

_frontend_build = Path(__file__).parent.parent / "frontend" / ".next"
if _frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_build), html=True), name="frontend")
