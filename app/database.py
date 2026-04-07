"""Optional MongoDB for roadmap mirror and question-bank documents."""
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

settings = get_settings()
client: Optional[AsyncIOMotorClient] = None
db: Optional[AsyncIOMotorDatabase] = None
users_collection: Any = None
assessments_collection: Any = None
skills_db_collection: Any = None
roadmaps_collection: Any = None
topic_notes_collection: Any = None
gamification_collection: Any = None
skillmap_collection: Any = None


def mongo_enabled() -> bool:
    return bool(settings.MONGODB_URI and settings.MONGODB_URI.strip())


def _db_name_from_uri(uri: str) -> str:
    _db_name = "learnova"
    if ".net/" in uri:
        try:
            _db_name = uri.split(".net/")[1].split("?")[0].strip("/") or "learnova"
        except Exception:
            pass
    elif uri.rstrip("/").split("/")[-1] and ":" not in uri.rstrip("/").split("/")[-1]:
        try:
            _db_name = uri.rstrip("/").split("/")[-1].split("?")[0] or "learnova"
        except Exception:
            pass
    return _db_name


def _ensure_client() -> None:
    global client, db, users_collection, assessments_collection, skills_db_collection, roadmaps_collection
    global topic_notes_collection, gamification_collection, skillmap_collection
    if not mongo_enabled():
        return
    if client is not None:
        return
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[_db_name_from_uri(settings.MONGODB_URI)]
    users_collection = db.users
    assessments_collection = db.assessments
    skills_db_collection = db.skills_database
    roadmaps_collection = db.roadmaps
    topic_notes_collection = db.topic_notes
    gamification_collection = db.gamification
    skillmap_collection = db.skill_map


async def get_database():
    _ensure_client()
    return db


async def init_db():
    """Create Mongo indexes when MongoDB is configured."""
    if not mongo_enabled():
        return
    _ensure_client()
    await users_collection.create_index("email", unique=True)
    await users_collection.create_index("user_id", unique=True)
    await assessments_collection.create_index("user_id")
    await roadmaps_collection.create_index("user_id")
    await topic_notes_collection.create_index([("user_id", 1), ("topic_id", 1)], unique=True)
    await gamification_collection.create_index("user_id", unique=True)
    await skillmap_collection.create_index([("user_id", 1), ("topic_id", 1)], unique=True)


async def mirror_roadmap_to_mongo(user_id: str, doc: dict) -> None:
    if not mongo_enabled():
        return
    _ensure_client()
    await roadmaps_collection.update_one(
        {"user_id": user_id},
        {"$set": doc},
        upsert=True,
    )
