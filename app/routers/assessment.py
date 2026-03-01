"""Assessment routes: Diagnostic test."""
from fastapi import APIRouter
from app.assessment_questions import get_questions_for_goal
from app.database import assessments_collection
from app.services.skill_profile import calculate_skill_scores
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/assessment", tags=["assessment"])


class AnswerItem(BaseModel):
    skill: str
    question_id: str
    answer: str


class AssessmentSubmit(BaseModel):
    user_id: str
    answers: List[AnswerItem]


@router.get("/questions/{goal}")
async def get_questions(goal: str):
    """Get diagnostic questions for career goal."""
    questions = get_questions_for_goal(goal)
    return {"questions": questions}


@router.post("/submit")
async def submit_assessment(data: AssessmentSubmit):
    """Submit assessment answers, calculate scores, store result."""
    answers = [a.model_dump() for a in data.answers]
    scores = calculate_skill_scores(answers, {})
    score_dict = {s.skill: s.score for s in scores}
    total = sum(score_dict.values()) / len(score_dict) if score_dict else 0

    doc = {
        "user_id": data.user_id,
        "answers": answers,
        "scores": [s.model_dump() for s in scores],
        "total_score": round(total, 1),
    }
    await assessments_collection.insert_one(doc)

    return {
        "user_id": data.user_id,
        "scores": [{"skill": s.skill, "score": s.score, "level": s.level.value} for s in scores],
        "total_score": round(total, 1),
    }
