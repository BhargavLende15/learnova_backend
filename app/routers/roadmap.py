"""Roadmap generation and fetch — Roadmap Agent + PostgreSQL (+ optional Mongo mirror)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import mirror_roadmap_to_mongo
from app.db_sql import get_db
from app.services.roadmap_agent import build_roadmap_payload
from app.sql_models import AssessmentResultRow, RoadmapRow, UserGoalSkills

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.post("/generate/{user_id}")
async def generate_roadmap(user_id: str, session: AsyncSession = Depends(get_db)):
    pref = await session.get(UserGoalSkills, user_id)
    if not pref:
        raise HTTPException(status_code=400, detail="Save career goal and skills first")

    r = await session.execute(
        select(AssessmentResultRow)
        .where(AssessmentResultRow.user_id == user_id)
        .order_by(AssessmentResultRow.created_at.desc())
        .limit(1)
    )
    res = r.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=400, detail="Complete and finalize the assessment first")

    skill_levels = res.skill_levels
    payload = build_roadmap_payload(pref.career_goal, skill_levels)

    row = await session.get(RoadmapRow, user_id)
    if row:
        row.career_goal = pref.career_goal
        row.payload = payload
    else:
        session.add(RoadmapRow(user_id=user_id, career_goal=pref.career_goal, payload=payload))
    await session.commit()

    await mirror_roadmap_to_mongo(
        user_id,
        {
            "user_id": user_id,
            "goal": pref.career_goal,
            "roadmap_payload": payload,
            "skills_gap": list(skill_levels.keys()),
        },
    )

    return {"user_id": user_id, "roadmap": payload}


@router.get("/{user_id}")
async def get_roadmap(user_id: str, session: AsyncSession = Depends(get_db)):
    row = await session.get(RoadmapRow, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Roadmap not found — call POST /roadmap/generate/{user_id}")
    return {"user_id": user_id, "career_goal": row.career_goal, "roadmap": row.payload}
