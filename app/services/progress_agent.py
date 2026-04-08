"""
Progress Agent — updates roadmap after completions and performance.
Skips mastered topics, accelerates on strong performance, adds review on struggle.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Set


def _all_topic_skill_map(phases: List[dict]) -> Dict[str, str]:
    m = {}
    for ph in phases:
        for t in ph.get("topics", []):
            m[t["id"]] = t.get("skill", "")
    return m


def apply_progress_update(
    roadmap_payload: dict,
    item_id: str,
    item_type: str,
    completed: bool,
    performance_score: float | None,
) -> dict:
    """Return updated roadmap payload (mutates a deep copy)."""
    data = copy.deepcopy(roadmap_payload)
    progress = data.setdefault("progress", {})
    completed_ids: List[str] = list(progress.get("completed_ids", []))
    perf = dict(progress.get("performance_by_item", {}))

    if performance_score is not None:
        perf[item_id] = performance_score
    if completed and item_id not in completed_ids:
        completed_ids.append(item_id)

    progress["completed_ids"] = completed_ids
    progress["performance_by_item"] = perf

    phases = data.get("phases", [])
    skill_map = _all_topic_skill_map(phases)
    skill = skill_map.get(item_id, "")

    # Strong performance → mark same-skill easier pending topics in Foundation as skippable
    if completed and performance_score is not None and performance_score >= 85 and skill:
        for ph in phases:
            if ph.get("name") != "Foundation":
                continue
            for t in ph.get("topics", []):
                if t.get("skill") == skill and t["id"] not in completed_ids:
                    t["suggested_skip"] = True
                    progress.setdefault("notes", []).append(
                        f"Accelerated: optional skip for {t['id']} based on strong {skill} performance."
                    )
                    break

    # Weak performance → inject review topic once per skill in Practice phase
    if completed and performance_score is not None and performance_score < 50 and skill:
        for ph in phases:
            if ph.get("name") != "Practice":
                continue
            rid = f"review_{skill[:6]}_{item_id[:6]}"
            if any(x.get("id") == rid for x in ph.get("topics", [])):
                break
            review_topic = {
                "id": rid,
                "title": f"Review: {skill} fundamentals (added after low score)",
                "skill": skill,
                "phase": "Practice",
                "estimated_hours": 4,
                "level": "Beginner",
                "injected": True,
            }
            ph.setdefault("topics", []).insert(0, review_topic)
            data.setdefault("item_index", []).append({"id": rid, "type": "topic"})
            progress.setdefault("notes", []).append(
                f"Review item added for {skill} due to performance below 50%."
            )
            break

    # Compress timelines slightly if many completions ahead of schedule
    done_set: Set[str] = set(completed_ids)
    total_items = len(data.get("item_index", [])) or 1
    if len(done_set) >= max(1, int(total_items * 0.4)):
        for ph in phases:
            w = ph.get("timeline_weeks", 4)
            ph["timeline_weeks"] = max(2, int(w * 0.9))

    # Hierarchical unlocking (linear by phase/topic order)
    ordered_topic_ids: List[str] = []
    for ph in phases:
        for t in ph.get("topics", []):
            tid = t.get("id")
            if tid:
                ordered_topic_ids.append(tid)
    unlocked: Set[str] = set(done_set)
    for tid in ordered_topic_ids:
        if tid not in done_set:
            unlocked.add(tid)
            break
    progress["unlocked_topic_ids"] = list(unlocked)

    data["phases"] = phases
    data["progress"] = progress
    return data
