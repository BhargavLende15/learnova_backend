"""Seed Skills Database with industry role requirements."""
import asyncio
from app.database import skills_db_collection, init_db

SKILLS_DATA = [
    {
        "role": "Data Scientist",
        "skills": ["Python", "Statistics", "Machine Learning", "Deep Learning", "SQL", "Data Visualization", "Pandas", "NumPy"],
        "description": "Data analysis, ML modeling, and statistical inference"
    },
    {
        "role": "Web Developer",
        "skills": ["HTML", "CSS", "JavaScript", "React", "Node.js", "Git", "REST API", "TypeScript"],
        "description": "Frontend and backend web development"
    },
    {
        "role": "AI Engineer",
        "skills": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "NLP", "Computer Vision", "MLOps"],
        "description": "Building and deploying AI/ML systems"
    }
]


async def seed_skills():
    """Seed skills database with role requirements."""
    await init_db()
    for role_data in SKILLS_DATA:
        await skills_db_collection.update_one(
            {"role": role_data["role"]},
            {"$set": role_data},
            upsert=True
        )
        print(f"Seeded: {role_data['role']}")
    print("Skills database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_skills())
