"""
Agentic AI Layer - Skill Analyzer, Industry Expert, Roadmap Agent, Mentor Agent.
Mentor chat uses the OpenAI API when OPENAI_API_KEY is set; otherwise rule-based fallback.
"""
import json
import logging
import os
import re
from typing import Any, List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
if settings.OPENAI_API_KEY:
    os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)


# ---------- Tool Functions (used by agents) ----------
def tool_skill_analyzer(assessment_scores: dict, goal: str) -> str:
    """Analyze assessment results and identify skill levels."""
    levels = []
    for skill, score in assessment_scores.items():
        if score < 30:
            levels.append(f"{skill}: Beginner ({score}%)")
        elif score < 70:
            levels.append(f"{skill}: Intermediate ({score}%)")
        else:
            levels.append(f"{skill}: Advanced ({score}%)")
    return f"Skill levels for {goal}: " + " | ".join(levels)


def tool_get_skill_gap(industry_skills: list, user_skills: dict) -> str:
    """Map skills to job role and find missing skills."""
    adequate = {s for s, v in user_skills.items() if (isinstance(v, (int, float)) and v >= 30)}
    gap = [s for s in industry_skills if s not in adequate]
    return f"Skill gap: {', '.join(gap) if gap else 'None'}" 


def tool_roadmap_suggestion(gap: list, scores: dict) -> str:
    """Generate roadmap sequence suggestion."""
    ordered = sorted(gap, key=lambda s: scores.get(s, 0))
    return "Recommended order: " + " → ".join(ordered[:6])


# ---------- Mentor Chat (AI) ----------
def _mentor_context_block(ctx: dict) -> str:
    slim: dict[str, Any] = {
        "career_goal": ctx.get("career_goal", ""),
        "selected_skills": ctx.get("selected_skills", []),
        "assessment_levels": ctx.get("assessment_levels", {}),
        "roadmap_phases": ctx.get("roadmap_phases", []),
        "roadmap_progress": ctx.get("roadmap_progress", {}),
        "completed_topics_count": len(ctx.get("completed_topic_ids") or []),
    }
    raw = json.dumps(slim, ensure_ascii=False, default=str)
    return raw[:14_000]


def _mentor_system_message(ctx: dict) -> str:
    return f"""You are Learnova Coach, a senior mentor for a personalized learning platform.

Use the JSON user context as ground truth. Personalize every answer; avoid vague generic advice.

You help with:
- Why this roadmap or skill order fits their goal
- What to learn next and how to start today
- Explaining roadmap phases or weekly focus
- Career guidance tied to their stated goal and skills
- Clearing up quiz/assessment doubts (explain concepts; never reveal correct answers or hidden solutions)
- Technology explanations in plain language
- Motivation without sounding repetitive

Rules:
- Reference specific skills, levels, or phase names from context when relevant.
- If context is thin, say what is missing (e.g. save goal/skills, finish assessment) and still give one useful next step.
- Keep answers scannable: short paragraphs or bullets, under ~280 words unless the user asks for depth.
- Never fabricate assessment scores or roadmap content; if missing, say so.

USER CONTEXT (JSON):
{_mentor_context_block(ctx)}
"""


def _sanitize_history(history: Optional[List[dict[str, str]]], limit: int = 24) -> List[dict[str, str]]:
    if not history:
        return []
    out: List[dict[str, str]] = []
    for turn in history[-limit:]:
        role = (turn.get("role") or "").strip().lower()
        content = (turn.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        out.append({"role": role, "content": content[:12_000]})
    return out


async def mentor_chat(
    user_id: str,
    message: str,
    context: Optional[dict] = None,
    history: Optional[List[dict[str, str]]] = None,
) -> str:
    """
    Contextual coach: roadmap rationale, next steps, quiz help, careers, motivation.
    Uses OpenAI when configured; otherwise rule-based fallback.
    """
    ctx = context or {}
    text = (message or "").strip()
    if not text:
        return "Ask me anything about your roadmap, skills, or next steps."

    s = get_settings()
    if not (s.OPENAI_API_KEY or "").strip():
        return _rule_based_mentor(text, ctx)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=s.OPENAI_API_KEY)
        system = _mentor_system_message(ctx)
        msgs: List[dict[str, str]] = [{"role": "system", "content": system}]
        for h in _sanitize_history(history):
            msgs.append(h)
        msgs.append({"role": "user", "content": text[:12_000]})

        comp = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.65,
            max_tokens=900,
            messages=msgs,
        )
        reply = (comp.choices[0].message.content or "").strip()
        if reply:
            return reply
    except Exception as exc:
        logger.warning("Mentor OpenAI chat failed, using rule-based fallback: %s", exc)

    return _rule_based_mentor(text, ctx)

def _rule_based_mentor(message: str, context: dict) -> str:
    """Structured fallback when OpenAI is unavailable."""
    msg = message.lower()
    goal = str(context.get("career_goal", "") or "")
    selected = context.get("selected_skills") or []
    levels = context.get("assessment_levels") or {}
    phases = context.get("roadmap_phases") or []
    done_n = len(context.get("completed_topic_ids") or [])

    phase_names = [p.get("name") for p in phases if isinstance(p, dict) and p.get("name")]
    first_topics: list[str] = []
    for p in phases:
        if isinstance(p, dict):
            first_topics.extend([t for t in (p.get("topic_titles") or [])[:3]])

    weakest = None
    if isinstance(levels, dict) and levels:
        try:

            def score_of(entry: Any) -> float:
                if isinstance(entry, dict):
                    return float(entry.get("score", 0))
                return 0.0

            weakest = min(levels.keys(), key=lambda k: score_of(levels.get(k)))
        except Exception:
            weakest = None

    if re.search(r"\bwhy\b.*\b(roadmap|mern|stack|path)", msg) or "why did i get" in msg:
        if goal:
            skills_txt = ", ".join(selected) if selected else "your selected skills"
            return (
                f"Your roadmap lines up with **{goal}**: Learnova orders skills from foundations toward job-ready depth, "
                f"using your assessment in {skills_txt}. "
                "If you picked a web stack, you will see HTML/CSS/JS before frameworks so components and routing sit on solid ground."
            )
        return "Save a career goal and skills on the dashboard, then finish the assessment — the roadmap is generated from that profile."

    if "what" in msg and "next" in msg:
        if weakest:
            return (
                f"Based on your latest levels, **{weakest}** has the most room to grow. "
                "Spend the next sessions on one narrow topic (for example one module + 5 practice items), then revisit a quick self-quiz."
            )
        if first_topics:
            return f"A concrete next step: open **{first_topics[0]}** on your roadmap and finish one small deliverable before moving on."
        return "Complete the adaptive assessment, generate your roadmap, then start the first unlocked topic in Practice."

    if "how long" in msg or "how many weeks" in msg or "timeline" in msg:
        wk = sum(int(p.get("weeks") or 0) for p in phases if isinstance(p, dict))
        if wk:
            return (
                f"Your visible phases add up to about **{wk} weeks** at a steady part-time pace (roughly 8–14 hours per week). "
                "Each week in the roadmap includes milestones and practice so the duration reflects depth, not padding."
            )
        return "After you generate a roadmap, open a phase to see per-week milestones and estimated effort."

    if "python" in msg and "why" in msg:
        return (
            "Python is a default backbone for data and AI roles because of its libraries and readability, "
            "and it is a productive first language for automation and APIs in web work too."
        )

    if "javascript" in msg and ("after" in msg or "next" in msg):
        return (
            "After JavaScript fundamentals, most web learners add **DOM/events**, then a framework (**React**), "
            "then **Node.js** for a full-stack picture — exactly the progression Learnova emphasizes for Web Developer goals."
        )

    if "mern" in msg or "mongo" in msg:
        return (
            "A MERN-style roadmap appears when your **Web Developer** selections include MongoDB-friendly paths "
            "or typical full-stack JavaScript skills — it reflects industry demand for React + Node APIs."
        )

    if "quiz" in msg or "assessment" in msg or "question" in msg:
        return (
            "Assessment questions adapt to your tier: if you are stuck, restate the concept in your own words, "
            "eliminate two wrong options by checking definitions, then pick the best fit. I cannot reveal answers, but I can explain ideas — tell me the topic name."
        )

    if "motivat" in msg or "stuck" in msg or "burnout" in msg:
        return (
            f"You already have **{done_n}** roadmap items completed — that is compounding evidence you can keep going. "
            "Shrink today’s goal to 25 focused minutes; momentum beats intensity."
        )

    if "roadmap" in msg or "phase" in msg:
        if phase_names:
            seq = " → ".join(phase_names)
            return f"Your phases run **{seq}**. Foundation builds vocabulary, Practice adds reps, Project validates with portfolio-style work."
        return "Generate your roadmap after the assessment to see Foundation → Practice → Project with weekly detail."

    if "start" in msg or "begin" in msg:
        return (
            "Today: (1) open Dashboard and confirm goal + skills, (2) run or review Assessment results, "
            "(3) on Roadmap, expand week 1 of Foundation and complete one practice task. "
            "That is enough for a strong start."
        )

    return (
        "I can explain your roadmap, suggest what to study next, estimate timelines, or unpack technologies. "
        f"Your saved goal is **{goal or 'not set yet'}**. What would you like to dig into?"
    )

# ---------- Agentic Workflow (orchestrator) ----------
async def run_agentic_workflow(
    user_id: str,
    goal: str,
    assessment_scores: dict,
    industry_skills: list,
) -> dict:
    """
    Full agentic workflow:
    Agent 1: Analyze skills -> Agent 2: Find gaps -> Agent 3: Create roadmap -> Agent 4: Explain
    """
    # Agent 1: Skill Analyzer
    skill_analysis = tool_skill_analyzer(assessment_scores, goal)

    # Agent 2: Industry Expert
    gap_analysis = tool_get_skill_gap(industry_skills, assessment_scores)
    gap_list = [s for s in industry_skills 
                if (isinstance(assessment_scores.get(s), (int, float)) and assessment_scores.get(s, 0) < 30) 
                or s not in assessment_scores]

    # Agent 3: Roadmap suggestion
    roadmap_hint = tool_roadmap_suggestion(gap_list, assessment_scores)

    # Agent 4: Mentor explanation (optional AI)
    al = {}
    for k, v in (assessment_scores or {}).items():
        if isinstance(v, (int, float)):
            al[k] = {"score": float(v)}
        elif isinstance(v, dict):
            al[k] = v
    explanation = await mentor_chat(
        user_id,
        f"Explain this roadmap to a user: {roadmap_hint}. Goal: {goal}. Skills: {skill_analysis}",
        {
            "career_goal": goal,
            "selected_skills": list(industry_skills or []),
            "assessment_levels": al,
            "roadmap_phases": [
                {"name": "Suggested order", "description": roadmap_hint, "topic_titles": list(gap_list or [])[:12]}
            ],
            "completed_topic_ids": [],
        },
    )

    return {
        "skill_analysis": skill_analysis,
        "gap_analysis": gap_analysis,
        "roadmap_hint": roadmap_hint,
        "explanation": explanation,
        "gap_list": gap_list,
    }
