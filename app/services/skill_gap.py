"""Skill Gap Analysis Engine - Compare user skills vs industry requirements."""
from typing import List
from app.database import skills_db_collection


async def get_industry_skills(role: str) -> List[str]:
    """Fetch required skills for a role from the skills database."""
    doc = await skills_db_collection.find_one({"role": role})
    if doc:
        return doc.get("skills", [])
    return []


def compute_skill_gap(industry_skills: List[str], user_skill_levels: dict) -> List[str]:
    """
    Compute gap: industry_skills - user_skills (where user is at least Intermediate).
    Skills user has at Beginner or doesn't have go into the gap.
    """
    INTERMEDIATE_THRESHOLD = 30  # 30%+ = we consider they "have" the skill
    user_skills_adequate = {
        s for s, level_or_score in user_skill_levels.items()
        if (isinstance(level_or_score, (int, float)) and level_or_score >= INTERMEDIATE_THRESHOLD)
        or (isinstance(level_or_score, str) and level_or_score.lower() in ("intermediate", "advanced"))
    }
    gap = [s for s in industry_skills if s not in user_skills_adequate]
    return gap
