import asyncio
from sqlalchemy import select
from app.db_sql import async_session_factory, init_sql_db
from app.sql_models import User, RoadmapRow
from app.database import init_db, skillmap_collection, mongo_enabled
from app.services.roadmap_agent import build_roadmap_payload

async def main():
    await init_sql_db()
    await init_db()
    
    async with async_session_factory() as session:
        # 1. find user
        r = await session.execute(select(User).where(User.email == user.email))
        user = r.scalar_one_or_none()
        if not user:
            print("User testuser@gmail.com not found!")
            return
        
        user_id = user.user_id
        print(f"Found User ID: {user_id}")
        
        # 2. Mock skill levels
        skill_levels = {
            "Python": {"level": "Intermediate", "score": 85.0},
            "Machine Learning": {"level": "Beginner", "score": 45.0},
            "Deep Learning": {"level": "Weak", "score": 20.0},
            "Data Visualization": {"level": "Advanced", "score": 95.0},
            "SQL": {"level": "Intermediate", "score": 75.0},
            "Pandas": {"level": "Intermediate", "score": 60.0},
        }
        
        # 3. Generate payload
        payload = build_roadmap_payload("Data Scientist", skill_levels)
        
        # 4. Save to RoadmapRow
        row = await session.get(RoadmapRow, user_id)
        if row:
            row.career_goal = "Data Scientist"
            row.payload = payload
        else:
            session.add(RoadmapRow(user_id=user_id, career_goal="Data Scientist", payload=payload))
        await session.commit()
        print("SQL RoadmapRow updated successfully.")
        
        # 5. Mirror to MongoDB for skill map extra details (if needed)
        if mongo_enabled():
            for sk, data in skill_levels.items():
                accuracy = data["score"]
                mastery = "Strong" if accuracy >= 80 else ("متوسط" if accuracy >= 50 else "Weak")
                # find topic_ids related to this skill in the payload
                for ph in payload.get("phases", []):
                    for t in ph.get("topics", []):
                        if t.get("skill") == sk:
                            await skillmap_collection.update_one(
                                {"user_id": user_id, "topic_id": t["id"]},
                                {"$set": {
                                    "user_id": user_id,
                                    "topic_id": t["id"],
                                    "accuracyPct": accuracy,
                                    "attempts": 2,
                                    "masteryLevel": mastery
                                }},
                                upsert=True
                            )
            print("MongoDB skillmap_collection updated successfully.")
            
if __name__ == "__main__":
    asyncio.run(main())
