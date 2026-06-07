"""Editor/segment endpoints."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import GENERATED_DIR
from src.routes.helpers import _load_json, _save_json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/book/{book_id}/preprocess/chapters")
async def get_chapters(book_id: str) -> dict[str, Any]:
    """Get chapter list with segment counts."""
    chapter_segments = _load_json(book_id, "chapter_segments.json")
    meta = _load_json(book_id, "meta.json")
    if not chapter_segments:
        raise HTTPException(status_code=404, detail="No preprocess data found.")
    return {"meta": meta, "chapters": chapter_segments}


@router.get("/api/book/{book_id}/preprocess/characters")
async def get_characters(book_id: str) -> dict[str, Any]:
    """Get character list with sheets and gender info."""
    llm_chars = _load_json(book_id, "llm_characters.json")
    genders = _load_json(book_id, "character_genders.json") or {}
    alias_map = _load_json(book_id, "alias_map.json") or {}

    # Find character sheet images — match by safe filename
    import re as _re
    chars_dir = GENERATED_DIR / book_id / "characters"
    sheets = {}
    if chars_dir.exists():
        sheet_files = {f.stem.replace("_sheet", ""): f for f in chars_dir.glob("*_sheet.*")}
        # Match each character's canonical name to a sheet file
        all_chars = llm_chars.get("characters", []) if llm_chars else []
        for char in all_chars:
            name = char.get("canonical_name", "")
            # Convert name to safe filename (same logic as character_sheet._safe_filename)
            safe = _re.sub(r'[^\w\s\u4e00-\u9fff-]', '', name)
            safe = _re.sub(r'\s+', '_', safe.strip()).lower()[:50]
            if safe in sheet_files:
                sheets[name] = f"/static/{book_id}/characters/{sheet_files[safe].name}"

    return {
        "characters": llm_chars.get("characters", []) if llm_chars else [],
        "genders": genders,
        "alias_map": alias_map,
        "sheets": sheets,
    }


@router.get("/api/book/{book_id}/preprocess/chapter/{ch_idx}/segments")
async def get_chapter_segments(book_id: str, ch_idx: int) -> dict[str, Any]:
    """Get all segments for a chapter with full data."""
    analysis = _load_json(book_id, "analysis.json")
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis data found.")

    segments = analysis.get("segments", [])
    ch_segments = [s for s in segments if s.get("chapter_idx") == ch_idx]

    # Add illustration paths if they exist
    ch_dir = GENERATED_DIR / book_id / "chapters" / f"ch{ch_idx:02d}"
    for seg in ch_segments:
        page_num = seg.get("id", 0) - min((s.get("id", 0) for s in ch_segments), default=0) + 1
        for ext in (".png", ".jpg"):
            img_path = ch_dir / "pages" / f"page_{page_num:03d}{ext}"
            if img_path.exists():
                seg["illustration_url"] = f"/static/{book_id}/chapters/ch{ch_idx:02d}/pages/{img_path.name}"
                break

    # Chapter info
    chapter_segments = _load_json(book_id, "chapter_segments.json") or {}
    ch_info = chapter_segments.get(str(ch_idx), {})

    return {
        "chapter_idx": ch_idx,
        "chapter_title": ch_info.get("chapter_title", f"Chapter {ch_idx + 1}"),
        "segments": ch_segments,
    }


class SegmentUpdate(BaseModel):
    text: Optional[str] = None
    simplified_text: Optional[str] = None
    characters_in_scene: Optional[list[str]] = None
    character_actions: Optional[list[dict[str, str]]] = None
    scene_background: Optional[str] = None
    scene_summary: Optional[str] = None
    sentiment: Optional[str] = None


@router.put("/api/book/{book_id}/segment/{seg_id}")
async def update_segment(book_id: str, seg_id: int, update: SegmentUpdate) -> dict[str, Any]:
    """Update a single segment's fields."""
    analysis = _load_json(book_id, "analysis.json")
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis data found.")

    segments = analysis.get("segments", [])
    target = None
    for seg in segments:
        if seg.get("id") == seg_id:
            target = seg
            break

    if target is None:
        raise HTTPException(status_code=404, detail=f"Segment {seg_id} not found.")

    # Apply updates
    update_dict = update.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        target[key] = value

    # Save back to JSON
    _save_json(book_id, "analysis.json", analysis)

    # Sync to MongoDB
    try:
        from src.core.db import update_segment as db_update_segment
        db_update_segment(book_id, seg_id, update_dict)
    except Exception:
        pass  # MongoDB is best-effort

    return {"status": "updated", "segment_id": seg_id, "updated_fields": list(update_dict.keys())}


@router.get("/api/book/{book_id}/segment/{seg_id}/history")
async def get_segment_illustration_history(book_id: str, seg_id: int) -> dict[str, Any]:
    """Get all historical illustrations for a segment."""
    analysis = _load_json(book_id, "analysis.json")
    if not analysis:
        return {"images": []}

    segments = analysis.get("segments", [])
    target = next((s for s in segments if s.get("id") == seg_id), None)
    if not target:
        return {"images": []}

    ch_idx = target.get("chapter_idx", 0)
    ch_segments = sorted([s for s in segments if s.get("chapter_idx") == ch_idx], key=lambda s: s.get("id", 0))
    page_num = next((i + 1 for i, s in enumerate(ch_segments) if s.get("id") == seg_id), 1)

    # Find all versions in pages dir + history dir
    images = []
    ch_dir = GENERATED_DIR / book_id / "chapters" / f"ch{ch_idx:02d}"
    pages_dir = ch_dir / "pages"
    history_dir = ch_dir / "history"

    # Current image + quality
    if pages_dir.exists():
        for ext in (".png", ".jpg"):
            current = pages_dir / f"page_{page_num:03d}{ext}"
            if current.exists():
                entry: dict[str, Any] = {
                    "url": f"/static/{book_id}/chapters/ch{ch_idx:02d}/pages/{current.name}",
                    "version": "current",
                    "timestamp": current.stat().st_mtime,
                }
                # Attach quality if exists
                qf = ch_dir / "quality" / f"page_{page_num:03d}_quality.json"
                if qf.exists():
                    entry["quality"] = json.loads(qf.read_text(encoding="utf-8"))
                images.append(entry)
                break

    # Historical images + quality
    if history_dir.exists():
        for f in sorted(history_dir.glob(f"page_{page_num:03d}_*.*"), reverse=True):
            if f.suffix == ".json":
                continue  # skip quality files, they're attached below
            version_ts = f.stem.split("_")[-1]
            entry = {
                "url": f"/static/{book_id}/chapters/ch{ch_idx:02d}/history/{f.name}",
                "version": version_ts,
                "timestamp": f.stat().st_mtime,
            }
            # Attach quality for this version
            qf = history_dir / f"page_{page_num:03d}_{version_ts}_quality.json"
            if qf.exists():
                entry["quality"] = json.loads(qf.read_text(encoding="utf-8"))
            images.append(entry)

    return {"images": images}


@router.post("/api/book/{book_id}/segment/{seg_id}/simplify")
async def simplify_segment_text(book_id: str, seg_id: int) -> dict[str, Any]:
    """Generate simplified text for a single segment."""
    analysis = _load_json(book_id, "analysis.json")
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis data.")
    target = next((s for s in analysis["segments"] if s.get("id") == seg_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Segment {seg_id} not found.")

    from src.agent.text_simplifier import simplify_text
    scene = {
        "page_number": 1,
        "original_text": target.get("text", ""),
        "key_characters": target.get("characters_in_scene", []),
        "scene_summary": target.get("scene_summary", ""),
    }
    result = simplify_text([scene], "4-6")
    simplified = result[0].get("page_text", "") if result else ""
    scene_direction = result[0].get("scene_direction", "") if result else ""

    # Save back
    target["simplified_text"] = simplified
    target["scene_direction"] = scene_direction
    _save_json(book_id, "analysis.json", analysis)

    return {"simplified_text": simplified, "scene_direction": scene_direction}


@router.post("/api/book/{book_id}/segment/{seg_id}/background")
async def generate_segment_background(book_id: str, seg_id: int) -> dict[str, Any]:
    """Generate scene background description for a single segment."""
    analysis = _load_json(book_id, "analysis.json")
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis data.")
    target = next((s for s in analysis["segments"] if s.get("id") == seg_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Segment {seg_id} not found.")

    from src.llm_client import generate_json
    result = generate_json(
        f"""Describe the physical setting/environment of this scene from a novel.
Be specific and visual: location, time of day, weather, objects, atmosphere, colors.

Scene text:
{target.get('text', '')[:1000]}

Return JSON: {{"scene_background": "detailed visual description..."}}"""
    )
    background = result.get("scene_background", "")

    target["scene_background"] = background
    _save_json(book_id, "analysis.json", analysis)

    return {"scene_background": background}


@router.post("/api/book/{book_id}/segment/{seg_id}/summarize")
async def summarize_segment(book_id: str, seg_id: int) -> dict[str, Any]:
    """Generate summary and sentiment for a single segment."""
    analysis = _load_json(book_id, "analysis.json")
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis data.")
    target = next((s for s in analysis["segments"] if s.get("id") == seg_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Segment {seg_id} not found.")

    from src.llm_client import generate_json
    result = generate_json(
        f"""Summarize this scene in one sentence. Also determine the sentiment.

Scene text:
{target.get('text', '')[:1000]}

Return JSON: {{"scene_summary": "one sentence summary", "sentiment": "positive/negative/neutral/tense/emotional"}}"""
    )
    summary = result.get("scene_summary", "")
    sentiment = result.get("sentiment", "neutral")

    target["scene_summary"] = summary
    target["sentiment"] = sentiment
    _save_json(book_id, "analysis.json", analysis)

    return {"scene_summary": summary, "sentiment": sentiment}


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []  # [{"role": "user"/"assistant", "content": "..."}]


@router.post("/api/book/{book_id}/segment/{seg_id}/chat")
async def chat_segment_prompt(book_id: str, seg_id: int, req: ChatRequest) -> dict[str, Any]:
    """AI assistant to help generate/refine illustration prompt fields via chat."""
    analysis = _load_json(book_id, "analysis.json")
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis data.")
    target = next((s for s in analysis["segments"] if s.get("id") == seg_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Segment {seg_id} not found.")

    # Build context from current segment
    context = (
        f"Original text:\n{target.get('text', '')[:1500]}\n\n"
        f"Current simplified_text: {target.get('simplified_text', '')}\n"
        f"Current scene_background: {target.get('scene_background', '')}\n"
        f"Current characters & actions: {json.dumps(target.get('character_actions', []), ensure_ascii=False)}\n"
        f"Current scene_summary: {target.get('scene_summary', '')}\n"
        f"Current sentiment: {target.get('sentiment', 'neutral')}\n"
    )

    system_prompt = """You are an illustration prompt assistant for a children's picture book generator.
The user is editing a page of a picture book adapted from a novel. They will describe what they want the illustration to look like, or ask you to adjust specific fields.

You have access to the current segment data (original text, simplified text, scene background, characters & actions, summary, sentiment).

Based on the user's request, return a JSON object with TWO keys:
1. "reply": a short, helpful response to the user (in the same language the user uses)
2. "updates": an object containing ONLY the fields that should be updated. Possible fields:
   - "simplified_text": the picture-book text for this page
   - "scene_background": visual description of the setting
   - "character_actions": array of {"name": "...", "action": "..."} objects
   - "scene_summary": one-sentence summary
   - "sentiment": one of "positive", "negative", "neutral", "tense", "emotional"

Only include fields in "updates" that the user wants to change. If the user is just asking a question, return empty updates {}.

Example response:
{"reply": "I've updated the background to a rainy night scene.", "updates": {"scene_background": "A dark, rainy night in London..."}}"""

    # Build conversation for LLM
    conversation = f"Current segment context:\n{context}\n\n"
    for msg in req.history[-10:]:  # keep last 10 messages
        role = msg.get("role", "user")
        conversation += f"{'User' if role == 'user' else 'Assistant'}: {msg['content']}\n"
    conversation += f"User: {req.message}"

    from src.llm_client import generate_json
    result = generate_json(conversation, system=system_prompt)

    reply = result.get("reply", "")
    updates = result.get("updates", {})

    # Apply updates to analysis
    if updates:
        for field in ("simplified_text", "scene_background", "scene_summary", "sentiment"):
            if field in updates:
                target[field] = updates[field]
        if "character_actions" in updates:
            target["character_actions"] = updates["character_actions"]
            target["characters_in_scene"] = [
                a["name"] for a in updates["character_actions"] if a.get("name")
            ]
        _save_json(book_id, "analysis.json", analysis)

    return {"reply": reply, "updates": updates}
