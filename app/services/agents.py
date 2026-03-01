"""
Agentic AI Layer - Skill Analyzer, Industry Expert, Roadmap Agent, Mentor Agent.
Uses LangChain with OpenAI. Falls back to rule-based logic if no API key.
"""
import os
from typing import Optional
from app.config import get_settings

settings = get_settings()
HAS_OPENAI = bool(settings.OPENAI_API_KEY)


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
async def mentor_chat(user_id: str, message: str, context: Optional[dict] = None) -> str:
    """
    AI Mentor Chatbot - Answers user questions about learning path.
    Uses OpenAI if available, else rule-based responses.
    """
    if not HAS_OPENAI:
        return _rule_based_mentor(message, context or {})

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        sys = """You are an AI career mentor for Learnova. Help users with:
        - What to learn next based on their skills
        - Motivation and study tips
        - Career advice for Data Scientist, Web Developer, AI Engineer roles
        Be concise and actionable."""

        ctx = context or {}
        user_ctx = f"\nUser context: goal={ctx.get('goal','')}, skills={ctx.get('skills',{})}, gap={ctx.get('gap',[])}"
        msgs = [
            SystemMessage(content=sys + user_ctx),
            HumanMessage(content=message),
        ]
        resp = await llm.ainvoke(msgs)
        return resp.content
    except Exception as e:
        return _rule_based_mentor(message, context or {}) + f" (AI unavailable: {e})"


def _rule_based_mentor(message: str, context: dict) -> str:
    """Fallback rule-based mentor when OpenAI is not available."""
    msg_lower = message.lower()
    gap = context.get("gap", [])
    skills = context.get("skills", {})
    goal = context.get("goal", "")

    if "next" in msg_lower or "learn" in msg_lower:
        if gap:
            return f"You should learn {gap[0]} next. It's a key skill for {goal} and you haven't mastered it yet."
        return "Great progress! Consider advanced projects or a new role goal."

    if "motivat" in msg_lower or "stuck" in msg_lower:
        return "Every expert was once a beginner. Focus on one skill at a time and practice daily. You've got this!"

    if "roadmap" in msg_lower:
        return f"Your roadmap for {goal}: " + " → ".join(gap[:5]) if gap else "Complete the assessment to get your roadmap."

    return "I'm your AI mentor! Ask me what to learn next, for motivation, or about your roadmap."


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
    explanation = await mentor_chat(
        user_id,
        f"Explain this roadmap to a user: {roadmap_hint}. Goal: {goal}. Skills: {skill_analysis}",
        {"goal": goal, "skills": assessment_scores, "gap": gap_list}
    )

    return {
        "skill_analysis": skill_analysis,
        "gap_analysis": gap_analysis,
        "roadmap_hint": roadmap_hint,
        "explanation": explanation,
        "gap_list": gap_list,
    }
