"""Skill Profile Generator - Converts scores to levels."""
from app.models import SkillLevel, SkillScore
from app.assessment_questions import ASSESSMENT_QUESTIONS


def score_to_level(score: float) -> SkillLevel:
    """Convert percentage score to skill level."""
    if score < 30:
        return SkillLevel.BEGINNER
    elif score < 70:
        return SkillLevel.INTERMEDIATE
    else:
        return SkillLevel.ADVANCED


def calculate_skill_scores(answers: list, questions_by_skill: dict) -> list[SkillScore]:
    """
    Calculate per-skill scores from assessment answers.
    Uses keyword/semantic matching (simplified) - in production use NLP/embeddings.
    """
    from difflib import SequenceMatcher

    def similarity(a: str, b: str) -> float:
        """Simple similarity score 0-1."""
        a_clean = a.lower().strip()
        b_clean = b.lower().strip()
        if not a_clean or not b_clean:
            return 0.0
        return SequenceMatcher(None, a_clean, b_clean).ratio()

    skill_totals = {}
    skill_counts = {}

    for ans in answers:
        ans_d = ans if isinstance(ans, dict) else {"skill": getattr(ans, "skill", ""), "answer": getattr(ans, "answer", ""), "question_id": getattr(ans, "question_id", "")}
        skill = ans_d.get("skill", "")
        answer_text = ans_d.get("answer", "")
        q_id = ans_d.get("question_id", "")

        # Find correct answer
        correct = ""
        for q in ASSESSMENT_QUESTIONS.get(skill, []):
            if q["question_id"] == q_id:
                correct = q["correct_answer"]
                break

        sim = similarity(answer_text, correct) if correct else 0
        # Threshold: 0.6+ = full credit, linear scale below
        points = min(1.0, sim / 0.6) if sim >= 0.3 else 0

        skill_totals[skill] = skill_totals.get(skill, 0) + points
        skill_counts[skill] = skill_counts.get(skill, 0) + 1

    result = []
    for skill, total in skill_totals.items():
        count = skill_counts[skill]
        score_pct = (total / count) * 100 if count else 0
        result.append(SkillScore(
            skill=skill,
            score=round(score_pct, 1),
            level=score_to_level(score_pct)
        ))
    return result
