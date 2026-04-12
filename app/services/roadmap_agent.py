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


def _week_detail(phase_name: str, week_num: int, skill: str, level: str) -> dict:
    """One calendar week of work: explicit tasks so total phase duration is credible."""
    lv = level or "Beginner"
    if phase_name == "Foundation":
        topics = [f"{skill} vocabulary & mental model", f"{skill} core building blocks", f"{skill} common pitfalls"]
        subtopics = {
            "Python": ["syntax & data types", "control flow", "functions & modules"],
            "JavaScript": ["values & types", "functions & scope", "DOM basics preview"],
            "React": ["components as functions", "JSX rules", "props flow"],
            "HTML": ["document structure", "semantic tags", "forms & inputs"],
            "CSS": ["selectors", "the box model", "typography basics"],
            "Node.js": ["runtime vs browser", "modules", "npm scripts"],
            "SQL": ["SELECT & filters", "JOIN intuition", "aggregations intro"],
            "Statistics": ["descriptive stats", "distributions", "sampling intuition"],
            "Machine Learning": ["supervised vs unsupervised", "train/val/test", "baseline metrics"],
            "Deep Learning": ["tensors & shapes", "layers intuition", "forward pass"],
        }.get(skill, ["core concepts", "guided examples", "short drills"])
        practice = [
            f"Complete 6–10 short exercises on {skill} fundamentals",
            f"Explain three ideas from this week aloud or in notes without looking them up",
        ]
        mini = [f"Micro-build: one small artifact using only {skill} basics (≤ 2 hours)"]
        revision = [f"Flash-review notes for {skill}", "Redo the hardest exercise once"]
        resources = [f"Official or primary docs for {skill}", "One video walkthrough at {lv} level"]
        milestone = f"Week {week_num}: You can read and write basic {skill} in isolation."
        hours = 8 if lv == "Beginner" else 10 if lv == "Intermediate" else 12
    elif phase_name == "Practice":
        topics = [f"{skill} patterns in small apps", f"{skill} debugging workflow", f"{skill} integration touchpoints"]
        subtopics = {
            "Python": ["file I/O & errors", "list/dict patterns", "simple CLI tool"],
            "JavaScript": ["events", "fetch & JSON", "small UI behavior"],
            "React": ["state lifting", "lists & keys", "effects for data"],
            "HTML": ["accessible components", "layout with structure", "embedding media"],
            "CSS": ["flexbox layouts", "responsive breakpoints", "component styling"],
            "Node.js": ["Express routes", "middleware chain", "env config"],
            "SQL": ["multi-table queries", "subqueries", "index awareness"],
            "Statistics": ["hypothesis intuition", "confidence framing", "simple A/B thinking"],
            "Machine Learning": ["feature ideas", "cross-validation", "error analysis"],
            "Deep Learning": ["overfitting signs", "regularization", "small model training loop"],
        }.get(skill, ["pattern practice", "integration drills", "debugging"])
        practice = [
            f"Timed practice set: 45–60 minutes focused on {skill}",
            f"Refactor yesterday’s solution to be clearer, not longer",
        ]
        mini = [f"Guided mini-project: combine {skill} with another skill you are learning"]
        revision = ["Notebook summary: 5 bullets of what stuck", "Retry one failed exercise"]
        resources = [f"Practice platform search for {skill}", "Official advanced-beginner module"]
        milestone = f"Week {week_num}: You can ship a small feature using {skill} with tests or checks."
        hours = 10 if lv == "Beginner" else 12 if lv == "Intermediate" else 14
    else:  # Project
        topics = [f"{skill} in portfolio scope", f"{skill} review & polish", f"{skill} demo narrative"]
        subtopics = {
            "Python": ["packaging & README", "edge cases", "lightweight tests"],
            "JavaScript": ["bundle basics awareness", "performance sanity", "lint/format"],
            "React": ["routing touch", "component boundaries", "deployment checklist"],
            "HTML": ["SEO/accessibility pass", "semantic audit", "performance basics"],
            "CSS": ["design consistency", "dark/light or themes optional", "print/responsive edge"],
            "Node.js": ["deployment or container intro", "logging", "simple auth awareness"],
            "SQL": ["schema justification", "query review", "data story"],
            "Statistics": ["clear charts", "assumptions stated", "limitations"],
            "Machine Learning": ["metric choice defense", "leakage check", "readme for reproducibility"],
            "Deep Learning": ["experiment log", "failure modes", "next steps"],
        }.get(skill, ["scope", "polish", "documentation"])
        practice = [
            f"End-to-end demo rehearsal for your {skill} contribution",
            "Peer or self code review using a short checklist",
        ]
        mini = [f"Portfolio milestone: integrate {skill} into the capstone slice"]
        revision = ["Record a 2-minute Loom-style explanation", "Update roadmap notes with gaps found"]
        resources = ["Style guide or rubric you will judge yourself against", "Example portfolio projects for tone"]
        milestone = f"Week {week_num}: You can present a credible portfolio slice featuring {skill}."
        hours = 12 if lv == "Beginner" else 14 if lv == "Intermediate" else 16

    return {
        "week": week_num,
        "focus_skill": skill,
        "title": f"Week {week_num}: {skill} — {phase_name}",
        "topics": topics,
        "subtopics": subtopics,
        "practice_tasks": practice,
        "mini_projects": mini,
        "revision_goals": revision,
        "useful_resources": resources,
        "milestone": milestone,
        "estimated_effort_hours": hours,
    }


def _weekly_breakdown(phase_name: str, week_count: int, skills_ordered: List[str], skill_levels: Dict[str, Dict[str, Any]]) -> List[dict]:
    if week_count <= 0 or not skills_ordered:
        return []
    weeks: List[dict] = []
    for w in range(1, week_count + 1):
        skill = skills_ordered[(w - 1) % len(skills_ordered)]
        lvl = skill_levels.get(skill, {}).get("level", "Beginner")
        weeks.append(_week_detail(phase_name, w, skill, str(lvl)))
    return weeks


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

        weekly_plan = _weekly_breakdown(phase_name, weeks, skills_ordered, skill_levels)
        phases.append(
            {
                "name": phase_name,
                "description": phase_desc,
                "timeline_weeks": weeks,
                "timeline_rationale": (
                    f"This {phase_name.lower()} phase spans {weeks} weeks so you can cycle through "
                    f"{len(skills_ordered)} skill area(s) with depth: weekly milestones, deliberate practice, "
                    "and revision — similar to a focused part-time bootcamp cadence (≈8–14 hours per week)."
                ),
                "weekly_breakdown": weekly_plan,
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
