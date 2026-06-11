"""Main pipeline: delegates to the Gemini Agent orchestrator.

Also provides MongoDB helpers for the FastAPI app to use.
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

import motor.motor_asyncio

from src.config import GENERATED_DIR, MONGODB_DB, MONGODB_URI
from src.core.models import (
    GenerationConfig,
    GenerationStatus,
    PictureBook,
    StatusEnum,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MongoDB helpers (used by FastAPI for status polling and book retrieval)
# ---------------------------------------------------------------------------

_mongo_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None


def _get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGODB_URI, serverSelectionTimeoutMS=5000
        )
    return _mongo_client[MONGODB_DB]


async def save_status(status: GenerationStatus) -> None:
    db = _get_db()
    await db.statuses.update_one(
        {"book_id": status.book_id},
        {"$set": status.model_dump()},
        upsert=True,
    )


async def save_book(book: PictureBook) -> None:
    db = _get_db()
    doc = book.model_dump()
    doc["created_at"] = book.created_at.isoformat()
    await db.books.update_one(
        {"book_id": book.book_id},
        {"$set": doc},
        upsert=True,
    )


async def get_status(book_id: str) -> Optional[dict[str, Any]]:
    db = _get_db()
    return await db.statuses.find_one({"book_id": book_id}, {"_id": 0})


async def get_book(book_id: str) -> Optional[dict[str, Any]]:
    db = _get_db()
    return await db.books.find_one({"book_id": book_id}, {"_id": 0})


async def list_books() -> list[dict[str, Any]]:
    try:
        db = _get_db()
        cursor = db.books.find(
            {},
            {"_id": 0, "book_id": 1, "title": 1, "created_at": 1, "config": 1},
        ).sort("created_at", -1)
        books = await cursor.to_list(length=200)
    except Exception as e:
        logger.warning("list_books: MongoDB unavailable, returning empty list (%s)", e)
        return []

    # Dedupe: per-chapter writes and case-variant book_ids create duplicate cards.
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for b in books:
        key = (b.get("book_id") or "").lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(b)
    return deduped


async def delete_book(book_id: str) -> bool:
    db = _get_db()
    # Books are stored one-doc-per-chapter — delete_one left the other chapters
    # behind, so the book "revived". Delete them all, and clear the consistency
    # collections too (characters/segments) instead of orphaning them.
    res = await db.books.delete_many({"book_id": book_id})
    await db.statuses.delete_one({"book_id": book_id})
    for coll in ("characters", "segments", "preprocess_files", "illustrations"):
        try:
            await db[coll].delete_many({"book_id": book_id})
        except Exception:
            pass
    # A preprocess-only book has a generated dir but no chapter docs yet — treat
    # that as deletable too, so the endpoint proceeds to rmtree instead of 404.
    from src.config import GENERATED_DIR
    has_dir = (GENERATED_DIR / book_id).exists()
    return res.deleted_count > 0 or has_dir


# ---------------------------------------------------------------------------
# NOTE: The Gemini function-calling orchestrator path (generate_picture_book →
# run_agent) was removed. The live pipeline runs via scripts/generate_chapter.py
# + src/agents/ (Analyzer→Writer→Artist→QA). This module now only provides the
# MongoDB status/book helpers above.
# ---------------------------------------------------------------------------
