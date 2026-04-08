"""Adaptive assessment — start, answer, finalize (Assessment Agent)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_sql import get_db
from app.services.assessment_agent import assessment_agent_singleton
from app.sql_models import AssessmentResultRow, AssessmentSessionRow, UserGoalSkills

router = APIRouter(prefix="/assessment", tags=["assessment"])


class StartBody(BaseModel):
    user_id: str
    skills: list[str] | None = None


class AnswerBody(BaseModel):
    session_id: str
    question_id: str
    selected_option: str


class FinalizeBody(BaseModel):
    session_id: str


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
    if not skills:
        pref = await db.get(UserGoalSkills, data.user_id)
        if not pref or not pref.selected_skills:
            raise HTTPException(
                status_code=400,
                detail="Select skills first or pass skills[] in start body",
            )
        skills = list(pref.selected_skills)

    st, payload = await assessment_agent_singleton.start_session(data.user_id, skills)
    payload = {**payload, "session_id": st.session_id}
    await _persist_session(db, assessment_agent_singleton.state_to_dict(st))
    return payload


@router.post("/answer")
async def submit_answer(data: AnswerBody, db: AsyncSession = Depends(get_db)):
    row = await db.get(AssessmentSessionRow, data.session_id)
    if not row or row.finalized:
        raise HTTPException(status_code=404, detail="Session not found or finalized")

    await assessment_agent_singleton.load_state_into_memory(data.session_id, row.state)
    st, result = await assessment_agent_singleton.submit_answer(
        data.session_id, data.question_id, data.selected_option
    )
    if not st:
        raise HTTPException(status_code=400, detail=result.get("error", "Bad request"))
    await _persist_session(db, assessment_agent_singleton.state_to_dict(st))
    return result


@router.post("/finalize")
async def finalize_assessment(data: FinalizeBody, db: AsyncSession = Depends(get_db)):
    row = await db.get(AssessmentSessionRow, data.session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.finalized:
        raise HTTPException(status_code=400, detail="Already finalized")

    await assessment_agent_singleton.load_state_into_memory(data.session_id, row.state)
    st = await assessment_agent_singleton.peek_session(data.session_id)
    if not st:
        raise HTTPException(status_code=400, detail="Session expired — restart assessment")

    summary = assessment_agent_singleton.finalize_levels(st)
    await _persist_session(db, assessment_agent_singleton.state_to_dict(st), finalized=True)

    db.add(
        AssessmentResultRow(
            user_id=st.user_id,
            session_id=data.session_id,
            skill_levels=summary["skill_levels"],
            raw_scores=summary["raw_scores"],
        )
    )
    await db.commit()

    return {
        "user_id": st.user_id,
        "session_id": data.session_id,
        "skill_levels": summary["skill_levels"],
        "raw_scores": summary["raw_scores"],
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
