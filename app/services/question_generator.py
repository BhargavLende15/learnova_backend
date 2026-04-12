"""
Dynamic MCQ generation for assessments — OpenAI when configured, else seeded procedural fallback.
Outputs are validated (4 options, correct ∈ options, non-empty stems).
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import uuid
from typing import Any, List, Optional, Tuple

from app.config import get_settings

_TIER_LABEL = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}

# Procedural fallback: (question, correct, distractors[3]) — not loaded from DB; used only if LLM unavailable.
_FALLBACK_BANK: dict[str, List[Tuple[str, str, Tuple[str, str, str]]]] = {
    "Python": [
        (
            "Which of the following best describes a Python list?",
            "An ordered, mutable sequence of items",
            ("An immutable mapping of keys to values", "A fixed-size array of bytes only", "A syntax for asynchronous I/O only"),
        ),
        (
            "What does `if __name__ == \"__main__\"` typically guard?",
            "Code that should run when the file is executed directly",
            ("Imports that must never execute", "Private class attributes", "Virtual environment activation"),
        ),
        (
            "Which statement about Python virtual environments is most accurate?",
            "They isolate project dependencies from the system interpreter",
            ("They compile Python to machine code", "They replace the need for pip", "They only work on Linux"),
        ),
        (
            "What is a generator function in Python?",
            "A function that uses `yield` to produce values lazily",
            ("A function that always returns a list", "A built-in for sorting iterables", "A decorator for caching results"),
        ),
        (
            "Which choice describes duck typing?",
            "An object is usable if it supports the needed methods, regardless of its class name",
            ("Types must be declared at compile time", "Only subclasses may replace base methods", "Inheritance depth determines behavior"),
        ),
    ],
    "JavaScript": [
        (
            "What is a closure in JavaScript?",
            "A function that retains access to variables from its enclosing lexical scope",
            ("A built-in method to close browser tabs", "A CSS technique for hiding elements", "A Promise that never resolves"),
        ),
        (
            "What does the event loop primarily coordinate?",
            "Callbacks, tasks, and microtasks after the call stack is clear",
            ("Synchronous parsing of HTML only", "GPU rendering in the browser", "Database transactions"),
        ),
        (
            "What is `async/await` primarily syntactic sugar for?",
            "Working with Promises in a linear readable style",
            ("Replacing all callbacks with threads", "Declaring static types", "Bundling modules for production"),
        ),
        (
            "What does `===` check that `==` does not guarantee?",
            "Type and value equality without coercion",
            ("Only reference equality", "Only numeric magnitude", "Prototype chain equality"),
        ),
    ],
    "React": [
        (
            "Which hook is most appropriate for subscribing to browser APIs or syncing with external systems?",
            "useEffect",
            ("useState", "useMemo", "useId"),
        ),
        (
            "What are props in React?",
            "Inputs passed from a parent component to configure a child",
            ("Internal mutable state only", "CSS class names reserved by React", "Server-only configuration"),
        ),
        (
            "What problem does the Virtual DOM help address?",
            "Efficiently determining minimal updates to the real DOM",
            ("Storing passwords securely", "Compressing bundle size automatically", "Replacing HTTP with WebSockets"),
        ),
    ],
    "HTML": [
        (
            "What is the main purpose of semantic HTML elements like `<article>` and `<nav>`?",
            "Convey meaning and structure to browsers, assistive tech, and developers",
            ("Force specific fonts in all browsers", "Obfuscate page source", "Disable CSS styling"),
        ),
        (
            "Why is the `<label>` element important for forms?",
            "It improves accessibility and focus behavior for controls",
            ("It encrypts user input", "It replaces server validation", "It blocks autofill"),
        ),
    ],
    "CSS": [
        (
            "What is CSS specificity used for?",
            "Deciding which rule wins when multiple selectors target the same element",
            ("Measuring page load time", "Choosing image formats", "Enabling server-side rendering"),
        ),
        (
            "When is Flexbox especially useful?",
            "One-dimensional layouts: aligning items along a row or column",
            ("3D transforms in WebGL", "Database normalization", "JWT signing"),
        ),
    ],
    "Node.js": [
        (
            "What is middleware in an Express-style app?",
            "Functions that run between receiving a request and sending a response",
            ("A database migration tool", "A React component", "A CSS preprocessor"),
        ),
        (
            "Why is Node.js well suited for I/O-heavy services?",
            "Its non-blocking event-driven model can handle many concurrent connections",
            ("It executes Python bytecode", "It compiles TypeScript in the browser", "It replaces DNS"),
        ),
    ],
    "SQL": [
        (
            "What does an INNER JOIN return?",
            "Rows where the join condition matches in both tables",
            ("All rows from the left table only", "Only unmatched rows", "Aggregates without grouping"),
        ),
        (
            "What is a primary key constraint intended to guarantee?",
            "Each row can be uniquely identified in its table",
            ("Columns may contain NULL everywhere", "Rows are physically sorted on disk", "Queries never need indexes"),
        ),
    ],
    "Statistics": [
        (
            "What does a confidence interval communicate?",
            "A plausible range for a parameter estimate given sample variability",
            ("The exact population value with certainty", "A proof of causation", "The p-value divided by two"),
        ),
        (
            "Why doesn't correlation imply causation?",
            "A third variable or directionality may explain the observed association",
            ("Correlation always equals zero", "Scatter plots cannot show trends", "Standard deviation removes linkage"),
        ),
    ],
    "Machine Learning": [
        (
            "What characterizes supervised learning?",
            "Training with labeled input-output pairs",
            ("Training without any inputs", "Optimizing only inference latency", "Learning solely from rewards without labels"),
        ),
        (
            "What is overfitting?",
            "The model fits training noise and generalizes poorly to new data",
            ("The model is too simple to learn patterns", "Training loss increases monotonically", "Gradients always vanish"),
        ),
    ],
    "Deep Learning": [
        (
            "What is the role of an activation function in a neural network?",
            "Introduce non-linearity so the network can represent complex functions",
            ("Normalize database schemas", "Encrypt model weights", "Replace the need for datasets"),
        ),
        (
            "What is transfer learning?",
            "Starting from a pretrained model and adapting it to a related task",
            ("Copying datasets between servers", "Training without validation", "Removing all layers"),
        ),
    ],
}


def _norm_stem(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())[:200]


def _bank_for_skill(skill: str) -> List[Tuple[str, str, Tuple[str, str, str]]]:
    if skill in _FALLBACK_BANK:
        return _FALLBACK_BANK[skill]
    # Merge similar stacks for skills without a bespoke list
    return _FALLBACK_BANK.get("Python", []) + _FALLBACK_BANK.get("Machine Learning", [])


def _fallback_mcq(
    skill: str,
    tier: int,
    session_id: str,
    avoid_stems: List[str],
) -> dict[str, Any]:
    bank = _bank_for_skill(skill)
    if not bank:
        bank = _FALLBACK_BANK["Python"]
    avoid = {_norm_stem(x) for x in avoid_stems}
    h = hashlib.sha256(f"{session_id}:{skill}:{tier}:{len(avoid)}".encode()).digest()
    seed = int.from_bytes(h[:8], "big")
    rng = random.Random(seed)
    order = list(range(len(bank)))
    rng.shuffle(order)
    chosen = None
    for i in order:
        q, c, dist = bank[i]
        if _norm_stem(q) not in avoid:
            chosen = (q, c, dist)
            break
    if not chosen:
        q, c, dist = bank[rng.randrange(len(bank))]
    else:
        q, c, dist = chosen
    opts = [c, dist[0], dist[1], dist[2]]
    rng.shuffle(opts)
    diff = _TIER_LABEL.get(max(1, min(3, tier)), "Intermediate")
    return {
        "question_id": f"ai_{uuid.uuid4().hex[:12]}",
        "question": q,
        "options": opts,
        "correct_answer": c,
        "difficulty": diff,
        "topic": skill,
        "explanation": f"The best choice is “{c}” because it matches standard definitions for {skill} at a {diff.lower()} level.",
    }


async def _openai_mcq(
    skill: str,
    tier: int,
    session_id: str,
    user_id: str,
    questions_answered: int,
    max_questions: int,
    avoid_stems: List[str],
) -> Optional[dict[str, Any]]:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return None

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    diff = _TIER_LABEL.get(max(1, min(3, tier)), "Intermediate")
    avoid_txt = "; ".join(avoid_stems[-12:]) if avoid_stems else "(none)"

    system = """You are an expert technical educator writing single-answer multiple-choice questions.
Rules:
- Output ONLY valid JSON, no markdown.
- Keys: question, options (array of exactly 4 distinct strings), correctAnswer (must equal exactly one element of options), difficulty, topic, explanation (1-3 sentences).
- Distractors must be plausible for someone studying the topic; no joke answers, no "all of the above".
- The question must be fresh and not a duplicate of any stem listed under avoidStems.
- Verify correctAnswer is verbatim one of options."""

    user_payload = {
        "skill": skill,
        "difficulty": diff,
        "roadmapDomain": skill,
        "progressStage": f"question {questions_answered + 1} of {max_questions}",
        "topic": skill,
        "sessionId": session_id,
        "userId": user_id,
        "avoidStems": avoid_stems[-20:],
    }

    try:
        comp = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.85,
            max_tokens=650,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": "Write one MCQ for adaptive assessment.",
                            "context": user_payload,
                            "avoidText": avoid_txt,
                        }
                    ),
                },
            ],
        )
        raw = (comp.choices[0].message.content or "").strip()
        data = json.loads(raw)
    except Exception:
        return None

    q = str(data.get("question", "")).strip()
    opts = data.get("options")
    ca = str(data.get("correctAnswer", data.get("correct_answer", ""))).strip()
    expl = str(data.get("explanation", "")).strip()
    topic = str(data.get("topic", skill)).strip() or skill
    diff_out = str(data.get("difficulty", diff)).strip() or diff

    if not q or not isinstance(opts, list) or len(opts) != 4:
        return None
    opts = [str(o).strip() for o in opts]
    if len({o.lower() for o in opts}) < 4:
        return None
    if ca not in opts:
        return None
    for stem in avoid_stems:
        if stem and _norm_stem(stem) == _norm_stem(q):
            return None

    return {
        "question_id": f"ai_{uuid.uuid4().hex[:12]}",
        "question": q,
        "options": opts,
        "correct_answer": ca,
        "difficulty": diff_out,
        "topic": topic,
        "explanation": expl or f"Correct: {ca}",
    }


async def generate_assessment_question(
    skill: str,
    tier: int,
    session_id: str,
    user_id: str,
    questions_answered: int,
    max_questions: int,
    avoid_stems: List[str],
) -> dict[str, Any]:
    """
    Returns a full question dict including server-only fields correct_answer and explanation.
    """
    out = await _openai_mcq(
        skill,
        tier,
        session_id,
        user_id,
        questions_answered,
        max_questions,
        avoid_stems,
    )
    if out:
        return out
    return _fallback_mcq(skill, tier, session_id, avoid_stems)


def public_question_view(q: dict) -> dict:
    """Strip fields that must not be sent to the client."""
    return {k: v for k, v in q.items() if k not in ("correct_answer", "explanation")}
