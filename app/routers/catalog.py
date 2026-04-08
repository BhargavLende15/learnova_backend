"""Fixed catalog — goals and skills (no free text)."""
from fastapi import APIRouter, HTTPException

from app.catalog_data import ALLOWED_GOALS, SKILLS_BY_GOAL

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/goals")
async def list_goals():
    return {"goals": ALLOWED_GOALS}


@router.get("/skills/{goal}")
async def list_skills_for_goal(goal: str):
    skills = SKILLS_BY_GOAL.get(goal)
    if not skills:
        raise HTTPException(status_code=404, detail="Unknown goal")
    return {"goal": goal, "skills": skills}
