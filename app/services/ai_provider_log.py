"""Terminal visibility for which LLM / fallback handled a request."""
from __future__ import annotations


def log_ai_provider(feature: str, provider: str) -> None:
    """Print one line to the server process stdout (e.g. uvicorn terminal)."""
    print(f"[Learnova AI] {feature}: {provider}", flush=True)
