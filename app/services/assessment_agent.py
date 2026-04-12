"""
Assessment Agent — adaptive difficulty, per-skill tracking, session state.
Questions are generated dynamically (LLM + procedural fallback), not from a static DB bank.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.models import SkillLevel
from app.services.question_generator import generate_assessment_question, public_question_view
from difflib import SequenceMatcher


def _similarity(a: str, b: str) -> float:
    a_clean = (a or "").lower().strip()
    b_clean = (b or "").lower().strip()
    if not a_clean or not b_clean:
        return 0.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def score_to_level(score: float) -> SkillLevel:
    if score < 40:
        return SkillLevel.BEGINNER
    if score < 70:
        return SkillLevel.INTERMEDIATE
    return SkillLevel.ADVANCED


@dataclass
class PerSkillState:
    difficulty: int = 2
    correct: int = 0
    wrong: int = 0
    used_ids: List[str] = field(default_factory=list)
    ability: float = 50.0


@dataclass
class SessionState:
    session_id: str
    user_id: str
    skills: List[str]
    skill_ptr: int = 0
    questions_answered: int = 0
    max_questions: int = 15
    per_skill: Dict[str, PerSkillState] = field(default_factory=dict)
    last_question: Optional[dict] = None
    history: List[dict] = field(default_factory=list)

    def __post_init__(self):
        for s in self.skills:
            if s not in self.per_skill:
                self.per_skill[s] = PerSkillState()


class AssessmentAgent:
    """Async agent with in-memory sessions + optional persistence hook."""

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    def _avoid_stems(self, st: SessionState) -> List[str]:
        stems: List[str] = []
        for h in st.history:
            stem = h.get("stem")
            if isinstance(stem, str) and stem.strip():
                stems.append(stem.strip())
        return stems

    async def start_session(self, user_id: str, skills: List[str]) -> Tuple[SessionState, dict]:
        sid = str(uuid.uuid4())
        st = SessionState(session_id=sid, user_id=user_id, skills=list(skills))
        async with self._lock:
            self._sessions[sid] = st
        q_payload = await self._next_question_payload_async(st)
        return st, q_payload

    def _pick_skill(self, st: SessionState) -> str:
        if not st.skills:
            return ""
        s = st.skills[st.skill_ptr % len(st.skills)]
        st.skill_ptr += 1
        return s

    async def _next_question_payload_async(self, st: SessionState) -> dict:
        if st.questions_answered >= st.max_questions or not st.skills:
            return {"done": True, "message": "You have reached the question limit — finalize to save your skill profile."}

        avoid = self._avoid_stems(st)

        for _attempt in range(len(st.skills) * 5):
            skill = self._pick_skill(st)
            ps = st.per_skill[skill]
            tier = max(1, min(3, ps.difficulty))

            q_full = await generate_assessment_question(
                skill=skill,
                tier=tier,
                session_id=st.session_id,
                user_id=st.user_id,
                questions_answered=st.questions_answered,
                max_questions=st.max_questions,
                avoid_stems=avoid,
            )

            qid = q_full["question_id"]
            if qid in ps.used_ids:
                continue
            ps.used_ids.append(qid)

            st.last_question = {
                "skill": skill,
                "question_id": qid,
                "question": q_full["question"],
                "options": q_full["options"],
                "difficulty_shown": tier,
                "difficulty_label": q_full.get("difficulty", "Intermediate"),
                "topic": q_full.get("topic", skill),
                "correct_answer": q_full["correct_answer"],
                "explanation": q_full.get("explanation", ""),
            }

            client_q = {
                **public_question_view(q_full),
                "skill": skill,
                "question_id": qid,
                "difficulty_tier": tier,
                "difficulty_label": q_full.get("difficulty", "Intermediate"),
                "topic": q_full.get("topic", skill),
            }

            return {
                "done": False,
                "session_id": st.session_id,
                "question": client_q,
            }

        return {"done": True, "message": "No more questions could be generated — finalize your assessment."}

    async def submit_answer(
        self, session_id: str, question_id: str, selected_option: str
    ) -> Tuple[Optional[SessionState], dict]:
        async with self._lock:
            st = self._sessions.get(session_id)
            if not st or not st.last_question:
                return None, {"error": "Invalid or expired session"}

            if st.last_question.get("question_id") != question_id:
                return st, {"error": "Question mismatch — reload the latest question."}

            skill = st.last_question["skill"]
            correct_text = st.last_question.get("correct_answer", "")
            explanation = st.last_question.get("explanation", "")
            stem = st.last_question.get("question", "")

            is_correct = _similarity(selected_option, correct_text) >= 0.55

            ps = st.per_skill[skill]
            tier = st.last_question.get("difficulty_shown", ps.difficulty)
            if is_correct:
                ps.correct += 1
                ps.difficulty = min(3, ps.difficulty + 1)
                ps.ability = min(100.0, ps.ability + 4.0 * tier)
            else:
                ps.wrong += 1
                ps.difficulty = max(1, ps.difficulty - 1)
                ps.ability = max(0.0, ps.ability - 5.0 * tier)

            st.history.append(
                {
                    "skill": skill,
                    "question_id": question_id,
                    "correct": is_correct,
                    "tier": tier,
                    "stem": stem,
                }
            )
            st.questions_answered += 1
            st.last_question = None

            next_q = await self._next_question_payload_async(st)
            return st, {
                "correct": is_correct,
                "explanation": explanation if explanation else None,
                "next": next_q,
            }

    def finalize_levels(self, st: SessionState) -> Dict[str, Any]:
        out = {}
        raw_scores = {}
        for skill in st.skills:
            ps = st.per_skill[skill]
            total = ps.correct + ps.wrong
            base = (ps.correct / total * 100.0) if total else ps.ability
            blended = 0.6 * ps.ability + 0.4 * base
            raw_scores[skill] = round(blended, 1)
            lvl = score_to_level(blended)
            out[skill] = {"level": lvl.value, "score": raw_scores[skill]}
        return {"skill_levels": out, "raw_scores": raw_scores}

    async def load_state_into_memory(self, session_id: str, state_dict: dict) -> SessionState:
        per: Dict[str, PerSkillState] = {}
        for k, v in state_dict.get("per_skill", {}).items():
            per[k] = PerSkillState(
                difficulty=int(v.get("difficulty", 2)),
                correct=int(v.get("correct", 0)),
                wrong=int(v.get("wrong", 0)),
                used_ids=list(v.get("used_ids", [])),
                ability=float(v.get("ability", 50.0)),
            )
        st = SessionState(
            session_id=state_dict["session_id"],
            user_id=state_dict["user_id"],
            skills=state_dict["skills"],
            skill_ptr=state_dict.get("skill_ptr", 0),
            questions_answered=state_dict.get("questions_answered", 0),
            max_questions=state_dict.get("max_questions", 15),
            per_skill=per,
            last_question=state_dict.get("last_question"),
            history=list(state_dict.get("history", [])),
        )
        async with self._lock:
            self._sessions[session_id] = st
        return st

    async def peek_session(self, session_id: str) -> Optional[SessionState]:
        async with self._lock:
            return self._sessions.get(session_id)

    def state_to_dict(self, st: SessionState) -> dict:
        return {
            "session_id": st.session_id,
            "user_id": st.user_id,
            "skills": st.skills,
            "skill_ptr": st.skill_ptr,
            "questions_answered": st.questions_answered,
            "max_questions": st.max_questions,
            "per_skill": {
                k: {
                    "difficulty": v.difficulty,
                    "correct": v.correct,
                    "wrong": v.wrong,
                    "used_ids": v.used_ids,
                    "ability": v.ability,
                }
                for k, v in st.per_skill.items()
            },
            "last_question": st.last_question,
            "history": st.history,
        }


assessment_agent_singleton = AssessmentAgent()
