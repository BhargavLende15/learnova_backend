"""Mentor chat — rich context from preferences, assessment, and roadmap."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_sql import get_db
from app.services.agents import mentor_chat
from app.sql_models import AssessmentResultRow, RoadmapRow, UserGoalSkills

router = APIRouter(prefix="/mentor", tags=["mentor"])


class MentorHistoryTurn(BaseModel):
    role: str
    content: str


class MentorRequest(BaseModel):
    user_id: str
    message: str
    history: list[MentorHistoryTurn] | None = None


@router.post("/chat")
async def mentor_chat_endpoint(data: MentorRequest, session: AsyncSession = Depends(get_db)):
    pref = await session.get(UserGoalSkills, data.user_id)
    r = await session.execute(
        select(AssessmentResultRow)
        .where(AssessmentResultRow.user_id == data.user_id)
        .order_by(AssessmentResultRow.created_at.desc())
        .limit(1)
    )
    assess_row = r.scalar_one_or_none()
    roadmap_row = await session.get(RoadmapRow, data.user_id)

    context: dict = {
        "career_goal": pref.career_goal if pref else "",
        "selected_skills": list(pref.selected_skills) if pref and pref.selected_skills else [],
        "assessment_levels": assess_row.skill_levels if assess_row else {},
        "roadmap_phases": [],
        "roadmap_progress": {},
        "completed_topic_ids": [],
    }

    if roadmap_row and roadmap_row.payload:
        pl = roadmap_row.payload
        context["roadmap_phases"] = [
            {
                "name": p.get("name"),
                "description": p.get("description"),
                "weeks": p.get("timeline_weeks"),
                "topic_titles": [t.get("title") for t in p.get("topics") or []][:12],
            }
            for p in (pl.get("phases") or [])
        ]
        progress = pl.get("progress") or {}
        context["roadmap_progress"] = progress
        context["completed_topic_ids"] = list(progress.get("completed_ids") or [])

    hist = (
        [{"role": t.role, "content": t.content} for t in (data.history or [])]
        if data.history
        else None
    )
    reply = await mentor_chat(data.user_id, data.message, context, history=hist)
    return {"reply": reply}
