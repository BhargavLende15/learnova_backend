from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from app.config import get_settings


def _extract_text_from_response(data: dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    for cand in candidates:
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        chunks: list[str] = []
        for p in parts:
            txt = p.get("text")
            if isinstance(txt, str) and txt.strip():
                chunks.append(txt)
        if chunks:
            return "\n".join(chunks).strip()
    return ""


def _strip_markdown_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


async def gemini_generate_text(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> Optional[str]:
    settings = get_settings()
    api_key = (settings.GEMINI_API_KEY or "").strip()
    model = (settings.GEMINI_MODEL or "gemini-1.5-flash").strip()
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "text/plain",
        },
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return None
            data = resp.json()
            return _extract_text_from_response(data) or None
    except Exception:
        return None


async def gemini_generate_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> Optional[dict[str, Any]]:
    settings = get_settings()
    api_key = (settings.GEMINI_API_KEY or "").strip()
    model = (settings.GEMINI_MODEL or "gemini-1.5-flash").strip()
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return None
            data = resp.json()
    except Exception:
        return None

    text = _extract_text_from_response(data)
    if not text:
        return None
    text = _strip_markdown_fences(text)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


def _ollama_url() -> str:
    s = get_settings()
    return (s.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")


def _ollama_model(explicit: Optional[str] = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    return (get_settings().OLLAMA_MODEL or "gemma3:1b-it-qat").strip()


async def ollama_generate_text(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> Optional[str]:
    url = f"{_ollama_url()}/api/generate"
    m = _ollama_model(model)
    prompt = f"System:\n{system_prompt.strip()}\n\nUser:\n{user_prompt.strip()}\n\nReply with plain text only."
    payload = {
        "model": m,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.5},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return None
            data = resp.json()
    except (httpx.TimeoutException, httpx.HTTPError, ValueError):
        return None
    except Exception:
        return None
    raw = data.get("response")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip()


async def ollama_generate_json(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> Optional[dict[str, Any]]:
    url = f"{_ollama_url()}/api/generate"
    m = _ollama_model(model)
    prompt = (
        f"System:\n{system_prompt.strip()}\n\n"
        f"User:\n{user_prompt.strip()}\n\n"
        "Return JSON only."
    )
    payload = {
        "model": m,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return None
            data = resp.json()
    except (httpx.TimeoutException, httpx.HTTPError, ValueError):
        return None
    except Exception:
        return None

    raw = data.get("response")
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = _strip_markdown_fences(raw)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None
