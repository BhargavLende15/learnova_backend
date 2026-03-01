"""Roadmap routes: Generate and fetch roadmap."""
from fastapi import APIRouter, HTTPException
from app.database import users_collection, assessments_collection, roadmaps_collection
from app.services.skill_gap import get_industry_skills, compute_skill_gap
from app.services.roadmap_generator import generate_roadmap
from app.services.agents import run_agentic_workflow

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("/{user_id}")
async def get_roadmap(user_id: str):
    """Generate or retrieve roadmap for user (with Agentic AI + Explainable AI)."""
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    goal = user.get("goal", "Data Scientist")
    current_level = user.get("current_level", "Beginner")

    # Get latest assessment
    assessment = await assessments_collection.find_one(
        {"user_id": user_id},
        sort=[("_id", -1)]
    )
    if not assessment:
        raise HTTPException(
            status_code=400,
            detail="Complete the diagnostic assessment first"
        )

    scores = {s["skill"]: s["score"] for s in assessment.get("scores", [])}
    industry_skills = await get_industry_skills(goal)
    skills_gap = compute_skill_gap(industry_skills, scores)

    # Run Agentic AI workflow (optional - adds explanation)
    agent_result = await run_agentic_workflow(
        user_id, goal, scores, industry_skills
    )
    gap_list = agent_result.get("gap_list", skills_gap)

    # Generate roadmap with explainable AI
    milestones, explanation = generate_roadmap(
        gap_list, scores, goal, current_level
    )

    # Check for existing roadmap and progress
    existing = await roadmaps_collection.find_one({"user_id": user_id})
    progress = existing.get("progress", {}) if existing else {}

    roadmap_doc = {
        "user_id": user_id,
        "goal": goal,
        "skills_gap": gap_list,
        "current_level": current_level,
        "roadmap": [m.model_dump() for m in milestones],
        "progress": progress,
        "explanation": explanation,
    }
    await roadmaps_collection.update_one(
        {"user_id": user_id},
        {"$set": roadmap_doc},
        upsert=True
    )

    return {
        "user_id": user_id,
        "goal": goal,
        "current_level": current_level,
        "skills_gap": gap_list,
        "roadmap": [{"month": m.month, "skill": m.skill, "reason": m.reason} for m in milestones],
        "progress": progress,
        "explanation": explanation,
        "agent_analysis": agent_result.get("skill_analysis"),
    }
