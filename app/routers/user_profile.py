from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_sql import get_db
from app.database import mirror_roadmap_to_mongo
from app.services.progress_agent import apply_progress_update
from app.sql_models import RoadmapRow, User
from app.deps import get_current_user


router = APIRouter(prefix="/api", tags=["profile"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_same_utc_day(a: datetime, b: datetime) -> bool:
    return a.date() == b.date()


class DailyLoginBody(BaseModel):
    userId: str = Field(min_length=1, max_length=64)


@router.post("/daily-login")
async def daily_login(
    body: DailyLoginBody,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if body.userId != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await session.get(User, body.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = _utcnow()
    earned = 0

    if user.last_active_date is None:
        user.streak = 1
        user.points = int(user.points or 0) + 10
        earned = 10
    else:
        last = user.last_active_date
        if _is_same_utc_day(last, now):
            earned = 0
        elif _is_same_utc_day(last, now - timedelta(days=1)):
            user.streak = int(user.streak or 0) + 1
            user.points = int(user.points or 0) + 10
            earned = 10
        else:
            user.streak = 1
            user.points = int(user.points or 0) + 10
            earned = 10

    user.last_active_date = now
    await session.commit()
    return {"ok": True, "earned": earned, "points": user.points, "streak": user.streak}


class CompleteTopicBody(BaseModel):
    userId: str = Field(min_length=1, max_length=64)
    topicId: str = Field(min_length=1, max_length=128)


@router.post("/complete-topic")
async def complete_topic(
    body: CompleteTopicBody,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if body.userId != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await session.get(User, body.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    completed = list(user.completed_topics or [])
    earned = 0
    if body.topicId not in completed:
        completed.append(body.topicId)
        user.completed_topics = completed
        user.points = int(user.points or 0) + 20
        earned = 20
    user.last_active_date = _utcnow()
    if not user.streak:
        user.streak = 1

    # Also update roadmap progress (topic done + unlock next)
    row = await session.get(RoadmapRow, body.userId)
    updated_roadmap = None
    if row:
        new_payload = apply_progress_update(row.payload, body.topicId, "topic", True, None)
        row.payload = new_payload
        await mirror_roadmap_to_mongo(
            body.userId,
            {"user_id": body.userId, "goal": row.career_goal, "roadmap_payload": new_payload},
        )
        updated_roadmap = new_payload

    await session.commit()
    return {"ok": True, "earned": earned, "points": user.points, "streak": user.streak, "roadmap": updated_roadmap}


@router.get("/profile/{user_id}")
async def get_profile(
    user_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    row = await session.get(RoadmapRow, user_id)
    total_topics = 0
    if row and row.payload:
        for ph in row.payload.get("phases") or []:
            total_topics += len(ph.get("topics") or [])

    completed_topics = list(user.completed_topics or [])
    recent = completed_topics[-8:][::-1]

    return {
        "userId": user.user_id,
        "name": user.name,
        "email": user.email,
        "points": int(user.points or 0),
        "streak": int(user.streak or 0),
        "lastActiveDate": user.last_active_date.isoformat() if user.last_active_date else None,
        "completedTopics": completed_topics,
        "recentCompletedTopics": recent,
        "totalTopics": total_topics,
    }

