"""Learnova - Career Roadmap AI System - FastAPI Backend."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import auth, assessment, roadmap, progress, mentor
from app.seed_skills import seed_skills


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB and seed skills."""
    await init_db()
    try:
        await seed_skills()
    except Exception:
        pass  # Continue if seed fails (e.g. already seeded)
    yield
    # Shutdown if needed


app = FastAPI(
    title="Learnova API",
    description="Career Roadmap AI - Skill Gap Analysis, Roadmap Generator, AI Mentor",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(assessment.router)
app.include_router(roadmap.router)
app.include_router(progress.router)
app.include_router(mentor.router)


@app.get("/")
async def root():
    return {
        "name": "Learnova",
        "description": "Career Roadmap AI System",
        "docs": "/docs",
        "endpoints": {
            "register": "POST /auth/register",
            "login": "POST /auth/login",
            "questions": "GET /assessment/questions/{goal}",
            "submit_assessment": "POST /assessment/submit",
            "roadmap": "GET /roadmap/{user_id}",
            "progress": "POST /progress/update",
            "mentor": "POST /mentor/chat",
        },
    }
