"""
Agentic AI Layer - Skill Analyzer, Industry Expert, Roadmap Agent, Mentor Agent.
Uses LangChain with OpenAI. Falls back to rule-based logic if no API key.
"""
import os
from typing import Optional
from app.config import get_settings

settings = get_settings()

import os
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY  

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
    AI Mentor Chatbot - Uses:
    1. OpenAI (if available)
    2. Groq (FREE fallback)
    3. Rule-based fallback
    """

    ctx = context or {}

    # ---------- 1️⃣ OpenAI ----------
    if HAS_OPENAI:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=settings.OPENAI_API_KEY
            )

            sys = """You are an AI career mentor for Learnova.
            Give clear, practical, step-by-step advice."""

            msgs = [
                SystemMessage(content=sys + f"\nUser context: {ctx}"),
                HumanMessage(content=message),
            ]

            resp = await llm.ainvoke(msgs)
            return resp.content

        except Exception:
            pass  # fallback to Groq

    # ---------- 2️⃣ Groq (FREE) ----------
    try:
        from groq import Groq

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = f"""
        You are an AI career mentor.

        Goal: {ctx.get("goal")}
        Skills: {ctx.get("skills")}
        Gaps: {ctx.get("gap")}

        Question: {message}

        Give short, actionable guidance.
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
        )

        return chat_completion.choices[0].message.content

    except Exception:
        pass

    # ---------- 3️⃣ Rule-based ----------
    return _rule_based_mentor(message, ctx)

def _rule_based_mentor(message: str, context: dict) -> str:
    """Fallback rule-based mentor when OpenAI is not available."""

    msg_lower = message.lower()
    gap = context.get("gap", [])
    skills = context.get("skills", {})
    goal = context.get("goal", "")

    # 🔹 Learn next
    if "next" in msg_lower or "learn" in msg_lower:
        if gap:
            return f"You should learn '{gap[0]}' next for becoming a {goal}. Focus on basics and practice projects."
        return f"You are doing well in {goal}. Start building advanced projects now."

    # 🔹 Improve skills (NEW FIX 🔥)
    if "improve" in msg_lower or "progress" in msg_lower:
        if gap:
            return f"To improve, focus on these weak areas: {', '.join(gap[:3])}. Practice consistently and revise concepts."
        return "Your skills look good. Try solving real-world problems and building projects."

    # 🔹 Motivation
    if "motivat" in msg_lower or "stuck" in msg_lower:
        return "You're not stuck, you're learning. Stay consistent, even 1% daily improvement is powerful."

    # 🔹 Roadmap
    if "roadmap" in msg_lower or "plan" in msg_lower:
        return f"Your roadmap for {goal}: " + " → ".join(gap[:5]) if gap else "Complete the assessment to generate your roadmap."

    # 🔹 Default (improved ❗)
    return f"For your goal '{goal}', focus on improving weak skills like {', '.join(gap[:2]) if gap else 'advanced topics'} and keep practicing."

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
