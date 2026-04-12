"""Static multi-question assessment — all items on one page; submit once, then roadmap."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment_questions import get_flat_questions_for_skills, prepare_public_questions, score_static_assessment
from app.db_sql import get_db
from app.sql_models import AssessmentResultRow, AssessmentSessionRow, UserGoalSkills

router = APIRouter(prefix="/assessment", tags=["assessment"])


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

    flat = get_flat_questions_for_skills(skills)
    if not flat:
        raise HTTPException(
            status_code=400,
            detail="No questions available for the selected skills — check catalog alignment.",
        )

    session_id = str(uuid.uuid4())
    questions = prepare_public_questions(skills, session_id)
    state_dict = {
        "session_id": session_id,
        "user_id": data.user_id,
        "mode": "static",
        "skills": skills,
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
    if st.get("mode") != "static":
        raise HTTPException(status_code=400, detail="Invalid or legacy session — start a new assessment")

    skills = list(st.get("skills") or [])
    if not skills:
        raise HTTPException(status_code=400, detail="Session has no skills")

    flat = get_flat_questions_for_skills(skills)
    required = [q["question_id"] for q in flat]
    ans = data.answers or {}
    missing = [qid for qid in required if not (str(ans.get(qid, "")).strip())]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Answer every question before generating your roadmap. Missing: {sorted(missing)}",
        )

    skill_levels, raw_scores = score_static_assessment(skills, ans)

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
    from app.assessment_questions import get_questions_for_goal

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
