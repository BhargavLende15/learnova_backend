"""Fixed catalog: no free-text goals or skills."""
from typing import Dict, List

ALLOWED_GOALS: List[str] = [
    "Data Scientist",
    "Web Developer",
    "AI Engineer",
]

# Skills available per goal (must match question bank keys in assessment_questions)
SKILLS_BY_GOAL: Dict[str, List[str]] = {
    "Data Scientist": ["Python", "Statistics", "Machine Learning", "SQL"],
    "Web Developer": ["HTML", "CSS", "JavaScript", "React", "Node.js"],
    "AI Engineer": ["Python", "Machine Learning", "Deep Learning", "SQL"],
}


def validate_goal(goal: str) -> bool:
    return goal in ALLOWED_GOALS


def validate_skills_for_goal(goal: str, skills: List[str]) -> tuple[bool, str]:
    if not validate_goal(goal):
        return False, "Invalid career goal"
    allowed = set(SKILLS_BY_GOAL.get(goal, []))
    if not skills:
        return False, "Select at least one skill"
    for s in skills:
        if s not in allowed:
            return False, f"Skill not allowed for this goal: {s}"
    return True, ""
