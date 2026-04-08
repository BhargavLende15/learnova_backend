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
resources_collection: Any = None


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
    global topic_notes_collection, gamification_collection, skillmap_collection, resources_collection
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
    resources_collection = db.resources


async def get_database():
    _ensure_client()
    return db


async def init_db():
    """Create Mongo indexes when MongoDB is configured."""
    if not mongo_enabled():
        return
    try:
        _ensure_client()
        print("MongoDB Connected")
        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("user_id", unique=True)
        await assessments_collection.create_index("user_id")
        await roadmaps_collection.create_index("user_id")
        await topic_notes_collection.create_index([("user_id", 1), ("topic_id", 1)], unique=True)
        await gamification_collection.create_index("user_id", unique=True)
        await skillmap_collection.create_index([("user_id", 1), ("topic_id", 1)], unique=True)
        await resources_collection.create_index("topic", unique=True)
        await resources_collection.create_index("createdAt")
    except Exception:
        # Mongo is optional. If it is configured but unavailable, keep the API up.
        return


async def mirror_roadmap_to_mongo(user_id: str, doc: dict) -> None:
    if not mongo_enabled():
        return
    _ensure_client()
    await roadmaps_collection.update_one(
        {"user_id": user_id},
        {"$set": doc},
        upsert=True,
    )

async def init_skillmap_in_mongo(user_id: str, payload: dict, skill_levels: dict) -> None:
    if not mongo_enabled():
        return
    _ensure_client()
    for ph in payload.get("phases", []):
        for t in ph.get("topics", []):
            sk = t.get("skill")
            if not sk:
                continue
            lvl_info = skill_levels.get(sk, {})
            accuracy = float(lvl_info.get("score", 0.0))
            mastery = "Strong" if accuracy >= 80 else ("متوسط" if accuracy >= 50 else "Weak")
            await skillmap_collection.update_one(
                {"user_id": user_id, "topic_id": t["id"]},
                {"$set": {
                    "user_id": user_id,
                    "topic_id": t["id"],
                    "accuracyPct": accuracy,
                    "attempts": 1,
                    "masteryLevel": mastery
                }},
                upsert=True,
            )

async def update_skillmap_in_mongo(user_id: str, topic_id: str, completed: bool, perf_score: float | None) -> None:
    if not mongo_enabled():
        return
    _ensure_client()
    doc = await skillmap_collection.find_one({"user_id": user_id, "topic_id": topic_id}) or {}
    attempts = doc.get("attempts", 0)
    current_acc = doc.get("accuracyPct", 0.0)
    if completed:
        attempts += 1
        
    new_acc = float(perf_score) if perf_score is not None else (100.0 if completed else current_acc)
    mastery = "Strong" if new_acc >= 80 else ("متوسط" if new_acc >= 50 else "Weak")
    
    await skillmap_collection.update_one(
        {"user_id": user_id, "topic_id": topic_id},
        {"$set": {
            "user_id": user_id,
            "topic_id": topic_id,
            "accuracyPct": new_acc,
            "attempts": attempts,
            "masteryLevel": mastery
        }},
        upsert=True,
    )
