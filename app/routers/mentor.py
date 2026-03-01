"""Mentor routes: AI Chat Mentor chatbot."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.agents import mentor_chat
from app.database import roadmaps_collection

router = APIRouter(prefix="/mentor", tags=["mentor"])


class MentorRequest(BaseModel):
    user_id: str
    message: str


@router.post("/chat")
async def mentor_chat_endpoint(data: MentorRequest):
    """AI Mentor Chatbot - User asks questions, agent replies with personalized advice."""
    doc = await roadmaps_collection.find_one({"user_id": data.user_id})
    context = {}
    if doc:
        context = {
            "goal": doc.get("goal", ""),
            "skills": doc.get("progress", {}),
            "gap": doc.get("skills_gap", []),
        }
    reply = await mentor_chat(data.user_id, data.message, context)
    return {"reply": reply}
