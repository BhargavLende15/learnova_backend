from __future__ import annotations

from dataclasses import dataclass
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
        {"title": "MDN / Web Docs search", "url": f"https://developer.mozilla.org/en-US/search?q={q}", "type": "docs"},
        {"title": "freeCodeCamp article search", "url": f"https://www.freecodecamp.org/news/search/?query={q}", "type": "blog"},
        {"title": "GeeksforGeeks search", "url": f"https://www.geeksforgeeks.org/?s={q}", "type": "blog"},
    ]
    videos = [
        {"title": "YouTube search", "url": f"https://www.youtube.com/results?search_query={q}", "type": "video"},
        {"title": "MIT OCW search", "url": f"https://ocw.mit.edu/search/?q={q}", "type": "video"},
    ]
    practice = generate_practice_links(topic_name)
    return GeneratedLinks(reading=reading, videos=videos, practice=practice)


def generate_practice_links(topic_name: str) -> list[dict]:
    q = _safe_q(topic_name)
    return [
        {"title": "LeetCode", "url": f"https://leetcode.com/problemset/?search={q}", "platform": "leetcode"},
        {"title": "HackerRank", "url": f"https://www.hackerrank.com/domains/tutorials/10-days-of-javascript?query={q}", "platform": "hackerrank"},
        {"title": "CodeChef", "url": f"https://www.codechef.com/problems/school?search={q}", "platform": "codechef"},
        {"title": "Codeforces", "url": f"https://codeforces.com/problemset?tags={q}", "platform": "codeforces"},
    ]

