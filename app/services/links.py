from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus


@dataclass(frozen=True)
class GeneratedLinks:
    reading: list[dict]
    videos: list[dict]
    practice: list[dict]


def _safe_q(s: str) -> str:
    return quote_plus((s or "").strip())


def generate_resource_links(topic_name: str) -> GeneratedLinks:
    """
    Production note:
    - If you want true "curated" results, wrap this with an LLM call and cache per topic.
    - This deterministic fallback is used when no LLM key/config is available.
    """
    q = _safe_q(topic_name)
    reading = [
        {
            "title": "MDN / Web Docs search",
            "url": f"https://developer.mozilla.org/en-US/search?q={q}",
            "type": "docs",
            "description": (
                "What it teaches: authoritative web platform concepts (HTML, CSS, JavaScript, APIs) tied to standards. "
                "Why it matters: accurate terminology and behavior so you debug real browsers, not myths. "
                "Who it is for: beginners through advanced front-end engineers. "
                f"Outcome: you can look up “{topic_name}” and apply official guidance with confidence."
            ),
        },
        {
            "title": "freeCodeCamp article search",
            "url": f"https://www.freecodecamp.org/news/search/?query={q}",
            "type": "blog",
            "description": (
                "What it teaches: approachable tutorials and roadmaps on coding careers and stacks. "
                "Why it matters: quick context and examples when you want a second explanation style. "
                "Who it is for: self-taught learners and career switchers. "
                f"Outcome: a clearer mental model of “{topic_name}” before you dive into projects."
            ),
        },
        {
            "title": "GeeksforGeeks search",
            "url": f"https://www.geeksforgeeks.org/?s={q}",
            "type": "blog",
            "description": (
                "What it teaches: CS fundamentals, interview patterns, and concise topic summaries. "
                "Why it matters: bridges classroom theory with problem-solving drills. "
                "Who it is for: students and interview candidates. "
                f"Outcome: structured notes and practice angles on “{topic_name}”."
            ),
        },
    ]
    videos = [
        {
            "title": "YouTube search",
            "url": f"https://www.youtube.com/results?search_query={q}",
            "type": "video",
            "description": (
                "What it teaches: visual walkthroughs, live coding, and varied instructor styles. "
                "Why it matters: motion and narration help when text alone feels abstract. "
                "Who it is for: visual learners and anyone needing a quick demo. "
                f"Outcome: a concrete walkthrough related to “{topic_name}” that you can follow along."
            ),
        },
        {
            "title": "MIT OCW search",
            "url": f"https://ocw.mit.edu/search/?q={q}",
            "type": "video",
            "description": (
                "What it teaches: university-level lectures and materials on STEM topics. "
                "Why it matters: depth and rigor when you want theory behind the tool. "
                "Who it is for: motivated learners comfortable with structured courses. "
                f"Outcome: stronger foundations that support advanced work in “{topic_name}”."
            ),
        },
    ]
    practice = generate_practice_links(topic_name)
    return GeneratedLinks(reading=reading, videos=videos, practice=practice)


def generate_practice_links(topic_name: str) -> list[dict]:
    q = _safe_q(topic_name)
    return [
        {
            "title": "LeetCode",
            "url": f"https://leetcode.com/problemset/?search={q}",
            "platform": "leetcode",
            "description": (
                "What it teaches: algorithmic problem solving with rich test cases. "
                "Why it matters: sharpens patterns used in technical interviews. "
                "Who it is for: developers practicing coding discipline. "
                f"Outcome: repeatable strategies you can map to “{topic_name}” problems."
            ),
        },
        {
            "title": "HackerRank",
            "url": f"https://www.hackerrank.com/domains/tutorials/10-days-of-javascript?query={q}",
            "platform": "hackerrank",
            "description": (
                "What it teaches: structured tracks, timed challenges, and language basics. "
                "Why it matters: steady skill ladders with immediate feedback. "
                "Who it is for: learners who want guided progression. "
                f"Outcome: hands-on reps that reinforce “{topic_name}” syntax and logic."
            ),
        },
        {
            "title": "CodeChef",
            "url": f"https://www.codechef.com/problems/school?search={q}",
            "platform": "codechef",
            "description": (
                "What it teaches: competitive-style problems and community contests. "
                "Why it matters: pushes edge-case thinking and speed. "
                "Who it is for: coders who enjoy ranked practice. "
                f"Outcome: stronger problem decomposition around “{topic_name}”."
            ),
        },
        {
            "title": "Codeforces",
            "url": f"https://codeforces.com/problemset?tags={q}",
            "platform": "codeforces",
            "description": (
                "What it teaches: ranked contests and tagged problem archives. "
                "Why it matters: exposes you to diverse trick patterns and proofs. "
                "Who it is for: intermediate+ programmers seeking challenge. "
                f"Outcome: depth beyond tutorials for topics adjacent to “{topic_name}”."
            ),
        },
    ]


def _splice_descriptions(items: list[dict], descs: list[str] | None) -> list[dict]:
    if not descs:
        return [dict(x) for x in items]
    out: list[dict] = []
    for i, item in enumerate(items):
        d = dict(item)
        if i < len(descs) and descs[i].strip():
            d["description"] = descs[i].strip()
        out.append(d)
    return out


def _merge_link_ai_descriptions(
    base: GeneratedLinks,
    data: dict[str, Any],
) -> GeneratedLinks | None:
    r_raw, v_raw, p_raw = data.get("reading"), data.get("videos"), data.get("practice")
    if not isinstance(r_raw, list) or not isinstance(v_raw, list) or not isinstance(p_raw, list):
        return None
    r = [str(x).strip() for x in r_raw]
    v = [str(x).strip() for x in v_raw]
    p = [str(x).strip() for x in p_raw]
    if len(r) != len(base.reading) or len(v) != len(base.videos) or len(p) != len(base.practice):
        return None
    if not any(r) and not any(v) and not any(p):
        return None
    return GeneratedLinks(
        reading=_splice_descriptions(base.reading, r),
        videos=_splice_descriptions(base.videos, v),
        practice=_splice_descriptions(base.practice, p),
    )


async def generate_resource_links_with_ai(topic_name: str) -> GeneratedLinks:
    """Same URLs as generate_resource_links; optional short AI descriptions (Gemini → Ollama)."""
    base = generate_resource_links(topic_name)
    topic = (topic_name or "").strip()
    if not topic:
        return base

    from app.services.ai_provider_log import log_ai_provider
    from app.services.gemini_client import gemini_generate_json, ollama_generate_json

    sys_p = (
        "Return JSON only. Keys: reading, videos, practice — arrays of short strings. "
        f"Exactly {len(base.reading)}, {len(base.videos)}, {len(base.practice)} items. "
        "Each string: one learning-focused blurb (max 25 words) for that slot; no URLs."
    )
    user_p = json.dumps({"topic": topic})
    payload = await gemini_generate_json(sys_p, user_p, temperature=0.35, max_output_tokens=450)
    merged = _merge_link_ai_descriptions(base, payload) if payload else None
    if merged:
        log_ai_provider("practice_resources", "gemini")
        return merged
    payload = await ollama_generate_json(sys_p, user_p, timeout_seconds=12.0)
    merged = _merge_link_ai_descriptions(base, payload) if payload else None
    if merged:
        log_ai_provider("practice_resources", "ollama")
        return merged
    log_ai_provider("practice_resources", "hardcoded")
    return base


async def generate_practice_links_with_ai(topic_name: str) -> list[dict]:
    """Practice links with optional AI-written descriptions."""
    base = generate_practice_links(topic_name)
    topic = (topic_name or "").strip()
    if not topic:
        return base

    from app.services.ai_provider_log import log_ai_provider
    from app.services.gemini_client import gemini_generate_json, ollama_generate_json

    n = len(base)
    sys_p = (
        "Return JSON only. Key practice: array of short strings. "
        f"Exactly {n} items. Each: max 25 words, why use that practice site for this topic. No URLs."
    )
    user_p = json.dumps({"topic": topic})
    payload = await gemini_generate_json(sys_p, user_p, temperature=0.35, max_output_tokens=320)
    pr = payload.get("practice") if isinstance(payload, dict) else None
    if isinstance(pr, list) and len(pr) == n and any(str(x).strip() for x in pr):
        log_ai_provider("practice_links", "gemini")
        return _splice_descriptions(base, [str(x).strip() for x in pr])
    payload = await ollama_generate_json(sys_p, user_p, timeout_seconds=10.0)
    pr = payload.get("practice") if isinstance(payload, dict) else None
    if isinstance(pr, list) and len(pr) == n and any(str(x).strip() for x in pr):
        log_ai_provider("practice_links", "ollama")
        return _splice_descriptions(base, [str(x).strip() for x in pr])
    log_ai_provider("practice_links", "hardcoded")
    return base

