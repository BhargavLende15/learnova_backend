"""Auth: register and login — users stored in PostgreSQL/SQLite."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, create_user_id, verify_password, create_access_token
from app.db_sql import get_db
from app.sql_models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register", response_model=dict)
async def register(data: UserRegister, session: AsyncSession = Depends(get_db)):
    r = await session.execute(select(User).where(User.email == data.email))
    if r.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = create_user_id()
    u = User(
        user_id=user_id,
        email=data.email,
        name=data.name,
        hashed_password=hash_password(data.password),
    )
    session.add(u)
    await session.commit()
    token = create_access_token({"sub": user_id, "email": data.email})
    return {
        "user_id": user_id,
        "name": data.name,
        "email": data.email,
        "token": token,
    }


@router.post("/login", response_model=dict)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_db)):
    r = await session.execute(select(User).where(User.email == data.email))
    user = r.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.user_id, "email": user.email})
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "token": token,
    }
