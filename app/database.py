"""MongoDB database connection and client."""
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings

settings = get_settings()
client = AsyncIOMotorClient(settings.MONGODB_URI)
# Extract db name from URI or use default
_db_name = "learnova"
uri = settings.MONGODB_URI
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
db = client[_db_name]

# Collection references
users_collection = db.users
assessments_collection = db.assessments
skills_db_collection = db.skills_database
roadmaps_collection = db.roadmaps


async def get_database():
    """Get database instance for dependency injection."""
    return db


async def init_db():
    """Initialize database with indexes and seed data if needed."""
    # Create indexes for better query performance
    await users_collection.create_index("email", unique=True)
    await users_collection.create_index("user_id", unique=True)
    await assessments_collection.create_index("user_id")
    await roadmaps_collection.create_index("user_id")
    await skills_db_collection.create_index("role", unique=True)
