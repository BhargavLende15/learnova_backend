"""Mentor chat — context from stored roadmap (SQL)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_sql import get_db
from app.services.agents import mentor_chat
from app.sql_models import RoadmapRow

router = APIRouter(prefix="/mentor", tags=["mentor"])


class MentorRequest(BaseModel):
    user_id: str
    message: str


@router.post("/chat")
async def mentor_chat_endpoint(data: MentorRequest, session: AsyncSession = Depends(get_db)):
    context = {}
    row = await session.get(RoadmapRow, data.user_id)
    if row and row.payload:
        pl = row.payload
        progress = pl.get("progress", {})
        context = {
            "goal": row.career_goal,
            "skills": progress.get("performance_by_item", {}),
            "gap": [p.get("name") for p in pl.get("phases", [])],
        }
    reply = await mentor_chat(data.user_id, data.message, context)
    return {"reply": reply}
