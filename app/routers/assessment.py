"""Dynamic multi-question assessment — AI-first generation with deterministic fallback."""
import uuid
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment_questions import get_questions_for_goal
from app.db_sql import get_db
from app.models import SkillLevel
from app.services.question_generator import generate_assessment_question, public_question_view
from app.sql_models import AssessmentResultRow, AssessmentSessionRow, UserGoalSkills

router = APIRouter(prefix="/assessment", tags=["assessment"])

QUESTIONS_PER_SKILL = 5
# Spread difficulty across the five items per skill
TIER_CYCLE = [1, 2, 3, 2, 3]


class StartBody(BaseModel):
    user_id: str
    skills: list[str] | None = None


class SubmitAllBody(BaseModel):
    user_id: str
    session_id: str
    answers: dict[str, str]


async def _persist_session(session: AsyncSession, state_dict: dict, finalized: bool = False):
    row = await session.get(AssessmentSessionRow, state_dict["session_id"])
    if row:
        row.state = state_dict
        row.finalized = finalized
    else:
        session.add(
            AssessmentSessionRow(
                session_id=state_dict["session_id"],
                user_id=state_dict["user_id"],
                state=state_dict,
                finalized=finalized,
            )
        )
    await session.commit()


@router.post("/start")
async def start_assessment(data: StartBody, db: AsyncSession = Depends(get_db)):
    skills = data.skills
    pref = await db.get(UserGoalSkills, data.user_id)
    if not skills:
        if not pref or not pref.selected_skills:
            raise HTTPException(
                status_code=400,
                detail="Select skills first or pass skills[] in start body",
            )
        skills = list(pref.selected_skills)

    session_id = str(uuid.uuid4())
    questions_full: list[dict] = []
    avoid_stems: list[str] = []
    total_cap = max(1, len(skills) * QUESTIONS_PER_SKILL)
    for skill in skills:
        for i in range(QUESTIONS_PER_SKILL):
            t = TIER_CYCLE[i % len(TIER_CYCLE)]
            q = await generate_assessment_question(
                skill=skill,
                tier=t,
                session_id=session_id,
                user_id=data.user_id,
                questions_answered=len(questions_full),
                max_questions=total_cap,
                avoid_stems=avoid_stems,
            )
            q["skill"] = skill
            questions_full.append(q)
            avoid_stems.append(q.get("question", ""))

    if not questions_full:
        raise HTTPException(status_code=400, detail="Could not generate assessment questions")

    questions = [{**public_question_view(q), "skill": q.get("skill", "")} for q in questions_full]
    state_dict = {
        "session_id": session_id,
        "user_id": data.user_id,
        "mode": "ai_dynamic",
        "skills": skills,
        "questions_full": questions_full,
    }
    await _persist_session(db, state_dict, finalized=False)

    return {
        "session_id": session_id,
        "questions": questions,
        "done": False,
        "message": None,
    }


@router.post("/submit-all")
async def submit_all_assessment(data: SubmitAllBody, db: AsyncSession = Depends(get_db)):
    row = await db.get(AssessmentSessionRow, data.session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.finalized:
        raise HTTPException(status_code=400, detail="Assessment already submitted")
    if row.user_id != data.user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")

    st = row.state or {}
    if st.get("mode") != "ai_dynamic":
        raise HTTPException(status_code=400, detail="Invalid or legacy session — start a new assessment")

    skills = list(st.get("skills") or [])
    if not skills:
        raise HTTPException(status_code=400, detail="Session has no skills")

    full = list(st.get("questions_full") or [])
    required = [q.get("question_id", "") for q in full if q.get("question_id")]
    ans = data.answers or {}
    missing = [qid for qid in required if not (str(ans.get(qid, "")).strip())]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Answer every question before generating your roadmap. Missing: {sorted(missing)}",
        )

    skill_levels, raw_scores = _score_ai_assessment(full, skills, ans)

    row.finalized = True
    row.state = {**st, "submitted": True, "answers": ans}
    db.add(
        AssessmentResultRow(
            user_id=data.user_id,
            session_id=data.session_id,
            skill_levels=skill_levels,
            raw_scores=raw_scores,
        )
    )
    await db.commit()

    return {
        "user_id": data.user_id,
        "session_id": data.session_id,
        "skill_levels": skill_levels,
        "raw_scores": raw_scores,
    }


@router.get("/questions/{goal}")
async def legacy_questions(goal: str):
    """Legacy: list static questions for a goal (diagnostic view only)."""
    return {"questions": get_questions_for_goal(goal)}


@router.get("/latest-result/{user_id}")
async def latest_result(user_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(AssessmentResultRow)
        .where(AssessmentResultRow.user_id == user_id)
        .order_by(AssessmentResultRow.created_at.desc())
        .limit(1)
    )
    row = r.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="No assessment result")
    return {
        "user_id": row.user_id,
        "session_id": row.session_id,
        "skill_levels": row.skill_levels,
        "raw_scores": row.raw_scores,
    }


def _similarity(a: str, b: str) -> float:
    a_clean = (a or "").lower().strip()
    b_clean = (b or "").lower().strip()
    if not a_clean or not b_clean:
        return 0.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def _score_to_level(score: float) -> str:
    if score < 40:
        return SkillLevel.BEGINNER.value
    if score < 70:
        return SkillLevel.INTERMEDIATE.value
    return SkillLevel.ADVANCED.value


def _score_ai_assessment(
    questions_full: list[dict],
    skills: list[str],
    answers: dict[str, str],
) -> tuple[dict, dict]:
    by_skill: dict[str, list[dict]] = {s: [] for s in skills}
    for q in questions_full:
        skill = str(q.get("topic") or q.get("skill") or "").strip()
        if skill not in by_skill:
            by_skill[skill] = []
        by_skill[skill].append(q)

    skill_levels: dict[str, dict] = {}
    raw_scores: dict[str, float] = {}
    for skill, qs in by_skill.items():
        if not qs:
            raw_scores[skill] = 0.0
            skill_levels[skill] = {"level": _score_to_level(0.0), "score": 0.0}
            continue
        correct = 0
        for q in qs:
            qid = str(q.get("question_id", ""))
            ca = str(q.get("correct_answer", ""))
            sel = str(answers.get(qid, "")).strip()
            if sel and _similarity(sel, ca) >= 0.55:
                correct += 1
        pct = round((correct / len(qs)) * 100.0, 1)
        raw_scores[skill] = pct
        skill_levels[skill] = {"level": _score_to_level(pct), "score": pct}

    return skill_levels, raw_scores
