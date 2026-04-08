from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from jose import jwt

from app.auth import hash_password, verify_password
from app.config import get_settings
from app import database as db
from app.deps import get_current_user
from app.db_sql import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.sql_models import User as SqlUser


router = APIRouter(prefix="/api/auth", tags=["auth-mongo"])
settings = get_settings()


def generate_token(user_id: str) -> str:
    payload = {"userId": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


class RegisterBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)


@router.post("/register")
async def register(body: RegisterBody, session: AsyncSession = Depends(get_db)):
    if not db.mongo_enabled():
        raise HTTPException(status_code=500, detail="MongoDB is not enabled for auth")
    db._ensure_client()

    email = str(body.email).lower()
    existing = await db.users_collection.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = email  # using email as id for now; keep consistent everywhere
    hashed = hash_password(body.password)
    doc = {
        "_id": user_id,  # stable id for demo; replace with ObjectId in production
        "user_id": user_id,  # IMPORTANT: avoids unique index collisions on null
        "name": body.name,
        "email": email,
        "password": hashed,
        "points": 0,
        "streak": 0,
        "completedTopics": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.users_collection.insert_one(doc)
    print(f"[auth] user saved: {doc['_id']}")

    # Keep existing SQL-based parts of the app working by mirroring the user row to SQL.
    row = await session.get(SqlUser, user_id)
    if not row:
        session.add(
            SqlUser(
                user_id=user_id,
                email=email,
                name=body.name,
                hashed_password=hashed,
                points=0,
                streak=0,
                completed_topics=[],
            )
        )
        await session.commit()

    token = generate_token(doc["_id"])
    print("[auth] token generated (register)")
    return {"token": token, "user": {"id": doc["_id"], "name": doc["name"], "email": doc["email"]}}


class LoginBody(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
async def login(body: LoginBody, session: AsyncSession = Depends(get_db)):
    if not db.mongo_enabled():
        raise HTTPException(status_code=500, detail="MongoDB is not enabled for auth")
    db._ensure_client()

    email = str(body.email).lower()
    user = await db.users_collection.find_one({"email": email})
    if not user or not verify_password(body.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user.get("user_id") or user["_id"])
    # Ensure SQL mirror exists (for profile/points routes still backed by SQL).
    row = await session.get(SqlUser, user_id)
    if not row:
        session.add(
            SqlUser(
                user_id=user_id,
                email=email,
                name=user.get("name", ""),
                hashed_password=user.get("password", ""),
                points=0,
                streak=0,
                completed_topics=[],
            )
        )
        await session.commit()

    token = generate_token(user_id)
    print("[auth] token generated (login)")
    return {
        "token": token,
        "user": {"id": user_id, "name": user.get("name", ""), "email": user.get("email", "")},
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    print(f"[auth] /me userId={current_user.get('id')}")
    return {"user": current_user}

