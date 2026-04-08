from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.database import mongo_enabled, resources_collection, _ensure_client  # type: ignore
from app.deps import get_current_user


router = APIRouter(prefix="/api", tags=["resources"])

settings = get_settings()


_YT_RE = re.compile(r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_\-]{6,})")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_topic(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip()).lower()


def _validate_youtube(url: str) -> str:
    if not url or "watch?v=" not in url:
        raise HTTPException(status_code=502, detail="Invalid YouTube link generated")
    if not _YT_RE.search(url):
        raise HTTPException(status_code=502, detail="Invalid YouTube link generated")
    if url.rstrip("/") in ("https://www.youtube.com", "https://www.youtube.com/"):
        raise HTTPException(status_code=502, detail="YouTube homepage link rejected")
    return url


def _validate_gfg(url: str) -> str:
    if not url or "geeksforgeeks.org" not in url:
        raise HTTPException(status_code=502, detail="Invalid GFG link generated")
    if url.rstrip("/") in ("https://www.geeksforgeeks.org", "https://www.geeksforgeeks.org/"):
        raise HTTPException(status_code=502, detail="GFG homepage link rejected")
    if "practice" not in url and "problems" not in url:
        raise HTTPException(status_code=502, detail="GFG non-practice link rejected")
    return url


async def _youtube_best_video(topic: str) -> str:
    if not settings.YOUTUBE_API_KEY:
        raise HTTPException(status_code=503, detail="YOUTUBE_API_KEY not configured")

    q = f"{topic} tutorial"
    async with httpx.AsyncClient(timeout=15) as client:
        # First pass: most relevant
        r = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "part": "snippet",
                "type": "video",
                "maxResults": 5,
                "q": q,
                "safeSearch": "moderate",
                "relevanceLanguage": "en",
            },
        )
        r.raise_for_status()
        items = (r.json() or {}).get("items") or []
        video_ids = [it.get("id", {}).get("videoId") for it in items if it.get("id", {}).get("videoId")]
        if not video_ids:
            raise HTTPException(status_code=404, detail="No YouTube results for topic")

        # Second pass: sort by viewCount among top relevance results
        r2 = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "part": "statistics",
                "id": ",".join(video_ids[:5]),
            },
        )
        r2.raise_for_status()
        stats_items = (r2.json() or {}).get("items") or []
        view_map: dict[str, int] = {}
        for it in stats_items:
            vid = it.get("id")
            vc = int((it.get("statistics") or {}).get("viewCount") or 0)
            if vid:
                view_map[vid] = vc

        best = sorted(video_ids, key=lambda vid: view_map.get(vid, 0), reverse=True)[0]
        return _validate_youtube(f"https://www.youtube.com/watch?v={best}")


async def _gfg_best_link(topic: str) -> str:
    """
    Fetches GFG search results page and extracts the best matching practice/problem link.
    Strictly rejects homepage and non-practice URLs.
    """
    q = quote_plus(topic)
    # Prefer GFG practice search (more stable for "practice/problems" URLs).
    practice_url = f"https://practice.geeksforgeeks.org/explore/?query={q}"
    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={"User-Agent": "LearnovaBot/1.0"},
    ) as client:
        links: list[str] = []
        for url in (practice_url, f"https://www.geeksforgeeks.org/?s={q}"):
            try:
                r = await client.get(url)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select("a[href]"):
                    href = (a.get("href") or "").split("#")[0]
                    if "geeksforgeeks.org" not in href:
                        continue
                    if href.rstrip("/") in ("https://www.geeksforgeeks.org", "https://www.geeksforgeeks.org/"):
                        continue
                    if "/page/" in href:
                        continue
                    if "practice" not in href and "problems" not in href:
                        continue
                    links.append(href)
            except Exception:
                continue

        # Prefer URLs containing both "practice" and "problems", then shorter (more specific)
        def rank(u: str) -> tuple[int, int]:
            score = 0
            if "practice" in u:
                score += 2
            if "problems" in u:
                score += 2
            return (-score, len(u))

        links = sorted(set(links), key=rank)
        if not links:
            raise HTTPException(status_code=404, detail="No GFG practice results for topic")
        return _validate_gfg(links[0])


@router.get("/resources")
async def get_resources(topic: str = Query(min_length=1, max_length=200), _: dict = Depends(get_current_user)):
    norm = _norm_topic(topic)
    # Mongo is optional: if unavailable, we still fetch live (no caching).
    if mongo_enabled():
        try:
            _ensure_client()
            existing = await resources_collection.find_one({"topicNorm": norm}, {"_id": 0})
            if existing and existing.get("youtubeLink") and existing.get("gfgLink"):
                return {"youtubeLink": existing["youtubeLink"], "gfgLink": existing["gfgLink"]}
        except Exception:
            pass

    youtube = await _youtube_best_video(topic)
    gfg = await _gfg_best_link(topic)

    if mongo_enabled():
        try:
            _ensure_client()
            doc = {
                "topic": topic,
                "topicNorm": norm,
                "youtubeLink": youtube,
                "gfgLink": gfg,
                "source": "ai",
                "createdAt": _now_iso(),
            }
            await resources_collection.update_one({"topicNorm": norm}, {"$set": doc}, upsert=True)
        except Exception:
            pass
    return {"youtubeLink": youtube, "gfgLink": gfg}

