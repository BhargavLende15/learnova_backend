"""AI Roadmap Generator with Explainable AI - Generate learning sequence with reasons."""
from typing import List
from app.models import RoadmapMilestone, SkillLevel
from app.services.skill_gap import get_industry_skills


def _skill_priority_for_beginner() -> dict:
    """Base skill ordering for beginners (foundational first)."""
    return {
        "Python": 1, "HTML": 1, "CSS": 2, "JavaScript": 3,
        "Statistics": 2, "SQL": 2, "React": 4, "Node.js": 4,
        "Machine Learning": 3, "Deep Learning": 4,
        "Data Visualization": 3, "Pandas": 2, "NumPy": 2,
        "TensorFlow": 4, "PyTorch": 4, "NLP": 4, "Computer Vision": 4, "MLOps": 5,
        "Git": 2, "REST API": 3, "TypeScript": 3,
    }


def generate_roadmap(
    skills_gap: List[str],
    user_scores: dict,
    goal: str,
    current_level: str,
) -> tuple[List[RoadmapMilestone], str]:
    """
    Generate ordered roadmap with explainable reasons.
    Returns (milestones, explanation_text).
    """
    priority_map = _skill_priority_for_beginner()
    # Sort gap by priority (lower = learn first)
    sorted_gap = sorted(
        skills_gap,
        key=lambda s: (priority_map.get(s, 99), -user_scores.get(s, 0))
    )

    milestones = []
    explanations = []

    for i, skill in enumerate(sorted_gap[:6], 1):  # Max 6 months
        score = user_scores.get(skill, 0)
        reason = _explain_recommendation(skill, score, goal)
        milestones.append(RoadmapMilestone(month=i, skill=skill, reason=reason))
        explanations.append(f"Month {i}: {skill} - {reason}")

    explanation_text = " | ".join(explanations)
    return milestones, explanation_text


def _explain_recommendation(skill: str, score: float, goal: str) -> str:
    """Explainable AI: Why this skill is recommended."""
    if score < 30:
        req = "High" if skill in ["Python", "Statistics", "Machine Learning", "JavaScript"] else "Medium"
        return f"Score={score:.0f}%, Industry requirement={req}"
    elif score < 70:
        return f"Score={score:.0f}%, needs strengthening for {goal}"
    else:
        return f"Already at {score:.0f}%, focus on advanced topics"
