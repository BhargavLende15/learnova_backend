"""Adaptive Learning Module - Update roadmap based on progress."""
from typing import List
from app.models import RoadmapMilestone


def adapt_roadmap(
    current_roadmap: List[dict],
    completed_skills: List[str],
    skill_weeks_taken: dict,
) -> List[dict]:
    """
    Adapt roadmap: if user completes a skill faster, compress timeline.
    E.g. Python expected 4 weeks, done in 2 → move next skills earlier.
    """
    if not current_roadmap:
        return current_roadmap

    # Filter out completed skills from roadmap
    remaining = [m for m in current_roadmap if m.get("skill") not in completed_skills]
    if not remaining:
        return current_roadmap

    # Re-sequence months
    adapted = []
    for i, m in enumerate(remaining, 1):
        new_m = dict(m)
        new_m["month"] = i
        adapted.append(new_m)
    return adapted
