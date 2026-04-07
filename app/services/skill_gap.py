"""Skill gap vs industry — MongoDB catalog when available, else Python catalog."""
from typing import List

from app.catalog_data import SKILLS_BY_GOAL
from app.database import mongo_enabled, skills_db_collection


async def get_industry_skills(role: str) -> List[str]:
    """Fetch required skills for a role."""
    if mongo_enabled() and skills_db_collection is not None:
        doc = await skills_db_collection.find_one({"role": role})
        if doc:
            return doc.get("skills", [])
    return list(SKILLS_BY_GOAL.get(role, []))


def compute_skill_gap(industry_skills: List[str], user_skill_levels: dict) -> List[str]:
    """
    Compute gap: industry_skills - user_skills (where user is at least Intermediate).
    """
    INTERMEDIATE_THRESHOLD = 30
    user_skills_adequate = {
        s
        for s, level_or_score in user_skill_levels.items()
        if (
            isinstance(level_or_score, (int, float)) and level_or_score >= INTERMEDIATE_THRESHOLD
        )
        or (
            isinstance(level_or_score, str)
            and level_or_score.lower() in ("intermediate", "advanced")
        )
    }
    return [s for s in industry_skills if s not in user_skills_adequate]
