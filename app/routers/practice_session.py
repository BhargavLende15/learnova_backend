from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import (
    mongo_enabled,
    _ensure_client,  # type: ignore
    topic_notes_collection,
)
from app.services.links import generate_practice_links, generate_resource_links


router = APIRouter(tags=["practice"])


class GenerateBody(BaseModel):
    topic_name: str = Field(min_length=1, max_length=200)


@router.post("/generate-resources")
async def generate_resources(body: GenerateBody):
    links = generate_resource_links(body.topic_name)
    return {"topic_name": body.topic_name, "reading": links.reading, "videos": links.videos}


@router.post("/generate-practice-links")
async def generate_practice(body: GenerateBody):
    links = generate_practice_links(body.topic_name)
    return {"topic_name": body.topic_name, "practice": links}


class SaveNotesBody(BaseModel):
    userId: str = Field(min_length=1, max_length=64)
    topicId: str = Field(min_length=1, max_length=128)
    notes: str = Field(default="", max_length=10_000)


@router.post("/save-notes")
async def save_notes(body: SaveNotesBody):
    if not mongo_enabled():
        raise HTTPException(status_code=400, detail="MongoDB is not enabled")
    _ensure_client()
    now = datetime.now(timezone.utc).isoformat()
    await topic_notes_collection.update_one(
        {"user_id": body.userId, "topic_id": body.topicId},
        {"$set": {"notes": body.notes, "updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"ok": True}


@router.get("/save-notes")
async def get_notes(userId: str, topicId: str):
    if not mongo_enabled():
        return {"userId": userId, "topicId": topicId, "notes": ""}
    _ensure_client()
    doc = await topic_notes_collection.find_one({"user_id": userId, "topic_id": topicId})
    return {"userId": userId, "topicId": topicId, "notes": (doc or {}).get("notes", "")}

