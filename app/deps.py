from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings
from app import database as db


settings = get_settings()
bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")

    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("userId") or payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not db.mongo_enabled():
        raise HTTPException(status_code=500, detail="MongoDB is not enabled for auth")
    try:
        db._ensure_client()
        user = await db.users_collection.find_one({"_id": user_id}, {"password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user.get("_id"))
        user.pop("_id", None)
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Auth database unavailable")

