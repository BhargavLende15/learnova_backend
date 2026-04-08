"""Progress updates — Progress Agent adjusts roadmap dynamically."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import mirror_roadmap_to_mongo, update_skillmap_in_mongo
from app.db_sql import get_db
from app.services.progress_agent import apply_progress_update
from app.sql_models import RoadmapRow

router = APIRouter(prefix="/progress", tags=["progress"])


class ProgressUpdate(BaseModel):
    user_id: str
    item_id: str
    item_type: str  # "topic" | "project"
    completed: bool
    performance_score: float | None = None


@router.post("/update")
async def update_progress(data: ProgressUpdate, session: AsyncSession = Depends(get_db)):
    row = await session.get(RoadmapRow, data.user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    if data.item_type not in ("topic", "project"):
        raise HTTPException(status_code=400, detail="item_type must be topic or project")

    new_payload = apply_progress_update(
        row.payload,
        data.item_id,
        data.item_type,
        data.completed,
        data.performance_score,
    )
    row.payload = new_payload
    await session.commit()

    await mirror_roadmap_to_mongo(
        data.user_id,
        {
            "user_id": data.user_id,
            "goal": row.career_goal,
            "roadmap_payload": new_payload,
        },
    )
    
    if data.item_type == "topic":
        await update_skillmap_in_mongo(data.user_id, data.item_id, data.completed, data.performance_score)

    return {
        "user_id": data.user_id,
        "roadmap_updated": True,
        "roadmap": new_payload,
    }


@router.post("/unlock-next-topic")
async def unlock_next_topic(data: ProgressUpdate, session: AsyncSession = Depends(get_db)):
    """
    Compatibility endpoint for UI flows that call "unlock-next-topic" explicitly.
    Unlocking is computed as part of the roadmap payload update.
    """
    return await update_progress(data, session)


@router.post("/update-progress")
async def update_progress_alias(data: ProgressUpdate, session: AsyncSession = Depends(get_db)):
    """Compatibility alias for the requested `/update-progress` endpoint."""
    return await update_progress(data, session)
