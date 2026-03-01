"""Auth routes: Register, Login."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models import UserRegister
from app.database import users_collection
from app.auth import hash_password, create_user_id, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=dict)
async def register(data: UserRegister):
    """User registration with career goal selection."""
    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = create_user_id()
    doc = {
        "user_id": user_id,
        "name": data.name,
        "email": data.email,
        "goal": data.goal.value,
        "current_level": data.current_level.value,
        "hashed_password": hash_password(data.password),
    }
    await users_collection.insert_one(doc)
    token = create_access_token({"sub": user_id, "email": data.email})
    return {
        "user_id": user_id,
        "name": data.name,
        "email": data.email,
        "goal": data.goal.value,
        "current_level": data.current_level.value,
        "token": token,
    }


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login", response_model=dict)
async def login(data: LoginRequest):
    """User login."""
    user = await users_collection.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["user_id"], "email": user["email"]})
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
        "goal": user["goal"],
        "current_level": user["current_level"],
        "token": token,
    }
