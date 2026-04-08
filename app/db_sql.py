"""Async SQL engine and sessions."""
from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings
from app.sql_models import Base

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_sql_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migration for existing SQLite DBs (no Alembic in this repo).
        # Ensures new gamification columns exist on `users`.
        try:
            if settings.DATABASE_URL.startswith("sqlite"):
                cols = await conn.execute(text("PRAGMA table_info(users)"))
                existing = {row[1] for row in cols.fetchall()}
                if "points" not in existing:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0"))
                if "streak" not in existing:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0"))
                if "last_active_date" not in existing:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN last_active_date DATETIME"))
                if "completed_topics" not in existing:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN completed_topics JSON"))
        except Exception:
            # If migration fails, app can still run; endpoints will error clearly.
            pass
