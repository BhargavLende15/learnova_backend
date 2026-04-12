"""Learnova — adaptive assessment, roadmap, and progress (FastAPI)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.db_sql import init_sql_db
from app.routers import auth, assessment, roadmap, progress, mentor, catalog, user_prefs, skill_map
from app.routers.resources import router as resources_router
from app.routers.user_profile import router as profile_router
from app.routers.api_auth import router as api_auth_router
from app.routers.public_endpoints import router as public_router
from app.seed_skills import seed_skills

from app.config import get_settings

settings = get_settings()
print("API KEY:", settings.OPENAI_API_KEY[:10])

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_sql_db()
    await init_db()
    try:
        await seed_skills()
    except Exception:
        pass
    yield


app = FastAPI(
    title="Learnova API",
    description="Adaptive learning: goal/skills, assessment agent, roadmap agent, progress agent",
    version="2.0.0",
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
app.include_router(catalog.router)
app.include_router(user_prefs.router)
app.include_router(assessment.router)
app.include_router(roadmap.router)
app.include_router(progress.router)
app.include_router(mentor.router)
app.include_router(public_router)
app.include_router(resources_router)
app.include_router(profile_router)
app.include_router(api_auth_router)
app.include_router(skill_map.router)


@app.get("/")
async def root():
    return {
        "name": "Learnova",
        "version": "2.0.0",
        "docs": "/docs",
        "flow": "Login → POST /user/goal-skills → POST /assessment/start → /assessment/answer → /assessment/finalize → POST /roadmap/generate/{user_id} → GET /roadmap/{user_id} → POST /progress/update",
    }
