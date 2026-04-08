from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_sql import get_db
from app.sql_models import RoadmapRow
from app.database import mongo_enabled, _ensure_client, skillmap_collection  # type: ignore


router = APIRouter(tags=["skill-map"])


class SkillMapRequest(BaseModel):
    userId: str = Field(min_length=1, max_length=64)


def _bucket(perf: float | None) -> str:
    if perf is None:
        return "Weak"
    if perf < 50:
        return "Weak"
    if perf < 80:
        return "متوسط"
    return "Strong"


def _color(level: str) -> str:
    return {"Weak": "red", "متوسط": "yellow", "Strong": "green"}.get(level, "red")


@router.post("/get-skill-map-data")
async def get_skill_map_data(body: SkillMapRequest, session: AsyncSession = Depends(get_db)):
    row = await session.get(RoadmapRow, body.userId)
    if not row:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    payload = row.payload or {}
    completed = set((payload.get("progress") or {}).get("completed_ids") or [])
    perf_by = dict((payload.get("progress") or {}).get("performance_by_item") or {})

    topics: list[dict] = []
    for ph in payload.get("phases") or []:
        for t in ph.get("topics") or []:
            tid = t.get("id")
            if not tid:
                continue
            perf = perf_by.get(tid)
            try:
                perf = float(perf) if perf is not None else None
            except Exception:
                perf = None
            level = _bucket(perf if tid in completed else perf)
            topics.append(
                {
                    "topicId": tid,
                    "topicName": t.get("title") or tid,
                    "accuracyPct": perf if perf is not None else (100.0 if tid in completed else 0.0),
                    "attempts": 1 if tid in completed else 0,
                    "masteryLevel": level,
                    "color": _color(level),
                }
            )

    if mongo_enabled():
        _ensure_client()
        extra = {}
        async for d in skillmap_collection.find({"user_id": body.userId}, {"_id": 0}):
            extra[d.get("topic_id")] = d
        for it in topics:
            e = extra.get(it["topicId"])
            if not e:
                continue
            it["accuracyPct"] = e.get("accuracyPct", it["accuracyPct"])
            it["attempts"] = e.get("attempts", it["attempts"])
            it["masteryLevel"] = e.get("masteryLevel", it["masteryLevel"])
            it["color"] = _color(it["masteryLevel"])

    return {"userId": body.userId, "topics": topics}

