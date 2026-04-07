from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_sql import get_db
from app.database import mirror_roadmap_to_mongo
from app.services.progress_agent import apply_progress_update
from app.sql_models import RoadmapRow
from app.services.links import generate_practice_links, generate_resource_links
from app.routers.practice_session import save_notes, get_notes  # re-export behavior
from app.routers.skill_map import get_skill_map_data
from app.routers.gamification import update_gamification, get_gamification


router = APIRouter(tags=["public"])


class ProgressUpdate(BaseModel):
    user_id: str
    item_id: str
    item_type: str  # "topic" | "project"
    completed: bool
    performance_score: float | None = None


@router.post("/update-progress")
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
        {"user_id": data.user_id, "goal": row.career_goal, "roadmap_payload": new_payload},
    )
    return {"user_id": data.user_id, "roadmap_updated": True, "roadmap": new_payload}


@router.post("/unlock-next-topic")
async def unlock_next_topic(data: ProgressUpdate, session: AsyncSession = Depends(get_db)):
    return await update_progress(data, session)


class GenerateBody(BaseModel):
    topic_name: str


@router.post("/generate-resources")
async def generate_resources(body: GenerateBody):
    links = generate_resource_links(body.topic_name)
    return {"topic_name": body.topic_name, "reading": links.reading, "videos": links.videos}


@router.post("/generate-practice-links")
async def generate_practice(body: GenerateBody):
    return {"topic_name": body.topic_name, "practice": generate_practice_links(body.topic_name)}


# Notes / skill map / gamification are provided by their dedicated routers,
# but are also reachable here via imports (FastAPI uses function objects directly).
router.add_api_route("/save-notes", save_notes, methods=["POST"])
router.add_api_route("/save-notes", get_notes, methods=["GET"])
router.add_api_route("/get-skill-map-data", get_skill_map_data, methods=["POST"])
router.add_api_route("/update-gamification", update_gamification, methods=["POST"])
router.add_api_route("/update-gamification", get_gamification, methods=["GET"])

