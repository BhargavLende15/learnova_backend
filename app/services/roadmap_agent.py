"""
Roadmap Agent — builds a 3-phase roadmap: Foundation → Practice → Project
from career goal and per-skill levels from the assessment.
"""
from __future__ import annotations

import copy
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.services.ai_provider_log import log_ai_provider
from app.services.gemini_client import gemini_generate_json, ollama_generate_json

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
        "generation_source": "hardcoded",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phases": phases,
        "progress": {
            "completed_ids": [],
            "performance_by_item": {},
            "notes": [],
        },
        "item_index": item_ids,
    }


def _norm_phase_name(name: str) -> str:
    n = (name or "").strip().lower()
    if n.startswith("found"):
        return "Foundation"
    if n.startswith("prac"):
        return "Practice"
    if n.startswith("proj"):
        return "Project"
    return ""


def _pick_list(value: Any, default: list[str]) -> list[str]:
    if not isinstance(value, list):
        return default
    out = [str(x).strip() for x in value if str(x).strip()]
    return out or default


def _coerce_ai_roadmap(ai_payload: dict[str, Any], fallback: dict[str, Any], source: str) -> dict | None:
    phases_in = ai_payload.get("phases")
    if not isinstance(phases_in, list) or not phases_in:
        return None

    by_name: dict[str, dict[str, Any]] = {}
    for ph in phases_in:
        if not isinstance(ph, dict):
            continue
        n = _norm_phase_name(str(ph.get("name", "")))
        if n:
            by_name[n] = ph

    out = dict(fallback)
    out["generation_source"] = source
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    out["career_goal"] = str(ai_payload.get("career_goal") or fallback.get("career_goal") or "")

    merged_phases: list[dict[str, Any]] = []
    for fb_phase in fallback.get("phases", []):
        fb_name = str(fb_phase.get("name", ""))
        ai_phase = by_name.get(fb_name, {})

        weeks_raw = ai_phase.get("timeline_weeks")
        weeks = fb_phase.get("timeline_weeks", 3)
        if isinstance(weeks_raw, int) and 1 <= weeks_raw <= 16:
            weeks = weeks_raw

        phase_out = dict(fb_phase)
        if isinstance(ai_phase.get("description"), str) and ai_phase["description"].strip():
            phase_out["description"] = ai_phase["description"].strip()
        if isinstance(ai_phase.get("timeline_rationale"), str) and ai_phase["timeline_rationale"].strip():
            phase_out["timeline_rationale"] = ai_phase["timeline_rationale"].strip()
        phase_out["timeline_weeks"] = weeks

        ai_weeks = ai_phase.get("weekly_breakdown")
        if isinstance(ai_weeks, list) and ai_weeks:
            base_weeks = phase_out.get("weekly_breakdown") or []
            merged_weeks: list[dict[str, Any]] = []
            for i, wb in enumerate(ai_weeks):
                default_w = base_weeks[i] if i < len(base_weeks) and isinstance(base_weeks[i], dict) else {}
                if not isinstance(wb, dict):
                    continue
                w = dict(default_w)
                w["week"] = int(wb.get("week")) if isinstance(wb.get("week"), int) else (i + 1)
                for key in ("focus_skill", "title", "milestone"):
                    val = wb.get(key)
                    if isinstance(val, str) and val.strip():
                        w[key] = val.strip()
                if isinstance(wb.get("estimated_effort_hours"), int):
                    w["estimated_effort_hours"] = wb["estimated_effort_hours"]
                for key in ("topics", "subtopics", "practice_tasks", "mini_projects", "revision_goals", "useful_resources"):
                    w[key] = _pick_list(wb.get(key), list(default_w.get(key) or []))
                merged_weeks.append(w)
            if merged_weeks:
                phase_out["weekly_breakdown"] = merged_weeks

        merged_phases.append(phase_out)

    if len(merged_phases) != 3:
        return None

    out["phases"] = merged_phases
    return out


async def build_roadmap_payload_ai(
    career_goal: str,
    skill_levels: Dict[str, Dict[str, Any]],
) -> dict:
    base = build_roadmap_payload(career_goal, skill_levels)
    base.setdefault("career_summary", "")
    base.setdefault("phase_personalization", {})
    base.setdefault("recommendations", [])

    def _debug_block(structure_source: str, personalization_source: str) -> None:
        print("==================================", flush=True)
        print(f"ROADMAP STRUCTURE: {structure_source}", flush=True)
        print(f"AI PERSONALIZATION: {personalization_source}", flush=True)
        print("==================================", flush=True)

    def _normalize_personalization(raw: dict[str, Any] | None) -> Optional[dict[str, Any]]:
        if not isinstance(raw, dict):
            return None

        summary = raw.get("career_summary")
        if summary is None:
            summary = raw.get("careerSummary")
        career_summary = summary.strip()[:1600] if isinstance(summary, str) else ""

        pp = raw.get("phase_personalization")
        if pp is None:
            pp = raw.get("phasePersonalization")
        phase_personalization: dict[str, str] = {}
        if isinstance(pp, dict):
            for phase_name in ("Foundation", "Practice", "Project"):
                val = pp.get(phase_name)
                if isinstance(val, str) and val.strip():
                    phase_personalization[phase_name] = val.strip()[:700]

        recs_raw = raw.get("recommendations")
        if recs_raw is None:
            recs_raw = raw.get("recommendation")
            if isinstance(recs_raw, str) and recs_raw.strip():
                recs_raw = [recs_raw]
        recommendations: list[str] = []
        if isinstance(recs_raw, list):
            for item in recs_raw:
                s = str(item).strip()
                if s:
                    recommendations.append(s[:220])
                if len(recommendations) >= 5:
                    break

        if not career_summary and not phase_personalization and not recommendations:
            return None

        return {
            "career_summary": career_summary,
            "phase_personalization": phase_personalization,
            "recommendations": recommendations,
        }

    def _merge_personalization(layer: dict[str, Any], source: str) -> dict:
        out = copy.deepcopy(base)
        out["generation_source"] = source
        out["generated_at"] = datetime.now(timezone.utc).isoformat()
        out["career_summary"] = layer.get("career_summary", "") or ""
        out["phase_personalization"] = layer.get("phase_personalization", {}) or {}
        out["recommendations"] = layer.get("recommendations", []) or []
        # Keep existing roadmap structure; only enrich with per-phase guidance text.
        phase_map = {str(p.get("name", "")): p for p in out.get("phases", []) if isinstance(p, dict)}
        for phase_name, text in out["phase_personalization"].items():
            if phase_name in phase_map and isinstance(text, str) and text.strip():
                phase_map[phase_name]["description"] = text.strip()
        return out

    compact_skill_levels: dict[str, Any] = {}
    for name, info in (skill_levels or {}).items():
        if not isinstance(name, str) or not isinstance(info, dict):
            continue
        compact_skill_levels[name] = {"level": info.get("level"), "score": info.get("score")}

    system_prompt = (
        "Return only JSON with keys: career_summary, phase_personalization, recommendations. "
        "phase_personalization must contain Foundation, Practice, Project. "
        "recommendations must have 3-5 short strings. No other keys. "
        "Do not generate roadmap phases, weeks, tasks, resources, or structure."
    )
    user_prompt = json.dumps(
        {"career_goal": career_goal, "skill_levels": compact_skill_levels},
        ensure_ascii=False,
    )[:6000]

    gemini_payload = await gemini_generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.35,
        max_output_tokens=420,
    )
    gemini_layer = _normalize_personalization(gemini_payload)
    if gemini_layer:
        log_ai_provider("roadmap", "gemini")
        _debug_block("HARDCODED", "GEMINI")
        return _merge_personalization(gemini_layer, "gemini")

    ollama_payload = await ollama_generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        timeout_seconds=10.0,
    )
    ollama_layer = _normalize_personalization(ollama_payload)
    if ollama_layer:
        log_ai_provider("roadmap", "ollama")
        _debug_block("HARDCODED", "OLLAMA")
        return _merge_personalization(ollama_layer, "ollama")

    out = copy.deepcopy(base)
    out["generation_source"] = "hardcoded"
    out["career_summary"] = out.get("career_summary") or ""
    out["phase_personalization"] = out.get("phase_personalization") or {}
    out["recommendations"] = out.get("recommendations") or []
    log_ai_provider("roadmap", "hardcoded")
    _debug_block("FULLY HARDCODED", "FAILED")
    return out
