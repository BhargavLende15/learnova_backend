from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import mongo_enabled, _ensure_client
from app import database as db


router = APIRouter(tags=["gamification"])


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_iso_date(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return datetime.fromisoformat(d.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _award_badges(points: int, score: float, efficiency: float, streak: int) -> list[str]:
    badges: set[str] = set()
    if points >= 2000:
        badges.add("Advanced")
    elif points >= 800:
        badges.add("Intermediate")
    else:
        badges.add("Beginner")
    if streak >= 7:
        badges.add("Consistency")
    if score >= 95:
        badges.add("Accuracy Master")
    if efficiency >= 90:
        badges.add("Efficiency Pro")
    return sorted(badges)


class UpdateGamificationBody(BaseModel):
    userId: str = Field(min_length=1, max_length=64)
    score: float = Field(ge=0, le=100)
    efficiency: float = Field(ge=0, le=100)


@router.post("/update-gamification")
async def update_gamification(body: UpdateGamificationBody):
    if not mongo_enabled():
        raise HTTPException(status_code=400, detail="MongoDB is not enabled")
    _ensure_client()

    today = _utc_today()
    existing = await db.gamification_collection.find_one({"user_id": body.userId}) or {}

    points = int(existing.get("points") or 0)
    streak = int(existing.get("streakCount") or 0)
    last_active = _parse_iso_date(existing.get("lastActiveDate"))
    yesterday = today - timedelta(days=1)

    if last_active == today:
        pass
    elif last_active == yesterday:
        streak += 1
    else:
        streak = 1

    gained = int(round(body.score * 8 + body.efficiency * 4))
    points += max(0, gained)

    badges = _award_badges(points=points, score=body.score, efficiency=body.efficiency, streak=streak)

    doc = {
        "user_id": body.userId,
        "points": points,
        "badges": badges,
        "streakCount": streak,
        "lastActiveDate": today.isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.gamification_collection.update_one({"user_id": body.userId}, {"$set": doc}, upsert=True)
    return {"ok": True, **doc}


@router.get("/update-gamification")
async def get_gamification(userId: str):
    if not mongo_enabled():
        return {"userId": userId, "points": 0, "badges": ["Beginner"], "streakCount": 0, "lastActiveDate": None}
    _ensure_client()
    doc = await db.gamification_collection.find_one({"user_id": userId}) or {}
    return {
        "userId": userId,
        "points": int(doc.get("points") or 0),
        "badges": list(doc.get("badges") or ["Beginner"]),
        "streakCount": int(doc.get("streakCount") or 0),
        "lastActiveDate": doc.get("lastActiveDate"),
    }

