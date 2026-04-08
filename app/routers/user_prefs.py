"""Persist user career goal and multi-selected skills after login."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog_data import validate_skills_for_goal
from app.db_sql import get_db
from app.sql_models import User, UserGoalSkills

router = APIRouter(prefix="/user", tags=["user"])


class GoalSkillsBody(BaseModel):
    user_id: str
    career_goal: str
    selected_skills: list[str]


@router.post("/goal-skills")
async def save_goal_skills(data: GoalSkillsBody, session: AsyncSession = Depends(get_db)):
    ok, msg = validate_skills_for_goal(data.career_goal, data.selected_skills)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    ur = await session.execute(select(User).where(User.user_id == data.user_id))
    if not ur.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    row = await session.get(UserGoalSkills, data.user_id)
    if row:
        row.career_goal = data.career_goal
        row.selected_skills = data.selected_skills
    else:
        session.add(
            UserGoalSkills(
                user_id=data.user_id,
                career_goal=data.career_goal,
                selected_skills=data.selected_skills,
            )
        )
    await session.commit()
    return {
        "user_id": data.user_id,
        "career_goal": data.career_goal,
        "selected_skills": data.selected_skills,
        "saved": True,
    }


@router.get("/goal-skills/{user_id}")
async def get_goal_skills(user_id: str, session: AsyncSession = Depends(get_db)):
    row = await session.get(UserGoalSkills, user_id)
    if not row:
        return {"user_id": user_id, "career_goal": None, "selected_skills": []}
    return {
        "user_id": user_id,
        "career_goal": row.career_goal,
        "selected_skills": row.selected_skills,
    }
