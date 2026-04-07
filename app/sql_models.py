"""SQLAlchemy ORM models — PostgreSQL (or SQLite for local demo)."""
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserGoalSkills(Base):
    """Career goal and multi-select skills (no free text — validated against catalog)."""
    __tablename__ = "user_goal_skills"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    career_goal: Mapped[str] = mapped_column(String(128))
    selected_skills: Mapped[list] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AssessmentSessionRow(Base):
    """Persists adaptive assessment session state for recovery and auditing."""
    __tablename__ = "assessment_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[dict] = mapped_column(JSON)
    finalized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssessmentResultRow(Base):
    """Final per-skill levels after assessment finalize."""
    __tablename__ = "assessment_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64))
    skill_levels: Mapped[dict] = mapped_column(JSON)
    raw_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RoadmapRow(Base):
    """Canonical roadmap in PostgreSQL; optionally mirrored to MongoDB."""
    __tablename__ = "roadmaps"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    career_goal: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
