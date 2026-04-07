"""
Roadmap Agent — builds a 3-phase roadmap: Foundation → Practice → Project
from career goal and per-skill levels from the assessment.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


def _resource(skill: str, phase: str, idx: int) -> dict:
    titles = {
        "Foundation": f"{skill}: core concepts and syntax",
        "Practice": f"{skill}: guided exercises and patterns",
        "Project": f"{skill}: applied mini-project brief",
    }
    return {
        "id": f"res_{phase[:4]}_{skill[:3]}_{idx}",
        "title": titles.get(phase, skill),
        "url": "https://learndemo.example.org/resources/placeholder",
        "type": "article" if phase == "Foundation" else "lab",
    }


def _mini_project(skill: str, phase: str, level: str) -> dict:
    return {
        "id": f"proj_{uuid.uuid4().hex[:8]}",
        "title": f"Validate {skill} — {phase} checkpoint",
        "skill": skill,
        "description": f"Apply {skill} at {level} level with a short scoped deliverable.",
        "rubric_criteria": ["Correctness", "Completeness", "Documentation"],
    }


def _topic(skill: str, phase: str, level: str, order: int) -> dict:
    depth = "basics" if level == "Beginner" else "intermediate patterns" if level == "Intermediate" else "advanced topics"
    return {
        "id": f"topic_{skill[:4]}_{phase[:3]}_{order}",
        "title": f"{skill} — {depth} ({phase})",
        "skill": skill,
        "phase": phase,
        "estimated_hours": 6 if level == "Beginner" else 10 if level == "Intermediate" else 14,
        "level": level,
    }


def build_roadmap_payload(
    career_goal: str,
    skill_levels: Dict[str, Dict[str, Any]],
) -> dict:
    """
    skill_levels: { "Python": {"level": "Beginner", "score": 42.0}, ... }
    """
    skills_ordered = sorted(
        skill_levels.keys(),
        key=lambda s: (
            {"Beginner": 0, "Intermediate": 1, "Advanced": 2}.get(
                skill_levels[s].get("level", "Beginner"), 0
            ),
            -float(skill_levels[s].get("score", 0)),
        ),
    )

    phases_meta: List[Tuple[str, str, int]] = [
        ("Foundation", "Core concepts and aligned fundamentals", 3),
        ("Practice", "Drills, small apps, and integration", 4),
        ("Project", "Portfolio-ready validation and review", 3),
    ]

    phases = []
    for phase_name, phase_desc, weeks in phases_meta:
        topics = []
        resources = []
        mini_projects = []
        for i, sk in enumerate(skills_ordered):
            lvl = skill_levels[sk].get("level", "Beginner")
            topics.append(_topic(sk, phase_name, lvl, i))
            resources.append(_resource(sk, phase_name, i))
            if phase_name in ("Practice", "Project"):
                mini_projects.append(_mini_project(sk, phase_name, lvl))

        phases.append(
            {
                "name": phase_name,
                "description": phase_desc,
                "timeline_weeks": weeks,
                "topics": topics,
                "resources": resources[: max(4, len(skills_ordered) * 2)],
                "mini_projects": mini_projects,
            }
        )

    item_ids = []
    for ph in phases:
        for t in ph["topics"]:
            item_ids.append({"id": t["id"], "type": "topic"})
        for p in ph.get("mini_projects", []):
            item_ids.append({"id": p["id"], "type": "project"})

    return {
        "career_goal": career_goal,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phases": phases,
        "progress": {
            "completed_ids": [],
            "performance_by_item": {},
            "notes": [],
        },
        "item_index": item_ids,
    }
