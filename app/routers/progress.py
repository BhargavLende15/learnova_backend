"""Progress routes: Adaptive learning updates."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import roadmaps_collection
from app.services.adaptive import adapt_roadmap

router = APIRouter(prefix="/progress", tags=["progress"])


class ProgressUpdate(BaseModel):
    user_id: str
    skill: str
    completed: bool
    weeks_taken: int | None = None


@router.post("/update")
async def update_progress(data: ProgressUpdate):
    """Update user progress - triggers adaptive roadmap adjustment."""
    doc = await roadmaps_collection.find_one({"user_id": data.user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    progress = doc.get("progress", {})
    progress[data.skill] = {
        "completed": data.completed,
        "weeks_taken": data.weeks_taken,
    }
    completed_skills = [s for s, p in progress.items() if p.get("completed")]

    # Adaptive: re-sequence roadmap
    current_roadmap = doc.get("roadmap", [])
    adapted = adapt_roadmap(
        current_roadmap,
        completed_skills,
        {s: p.get("weeks_taken", 4) for s, p in progress.items() if p.get("weeks_taken")}
    )

    await roadmaps_collection.update_one(
        {"user_id": data.user_id},
        {"$set": {"progress": progress, "roadmap": adapted}}
    )

    return {
        "user_id": data.user_id,
        "progress": progress,
        "roadmap_updated": True,
        "completed_skills": completed_skills,
    }
