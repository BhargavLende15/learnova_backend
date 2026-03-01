"""Pydantic models for API and database schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============ Enums ============
class CareerGoal(str, Enum):
    DATA_SCIENTIST = "Data Scientist"
    WEB_DEVELOPER = "Web Developer"
    AI_ENGINEER = "AI Engineer"


class SkillLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


# ============ User Models ============
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    goal: CareerGoal
    current_level: Optional[SkillLevel] = SkillLevel.BEGINNER


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    goal: str
    current_level: str


class UserInDB(BaseModel):
    user_id: str
    name: str
    email: str
    goal: str
    current_level: str
    hashed_password: str


# ============ Assessment Models ============
class QuestionAnswer(BaseModel):
    skill: str
    question_id: str
    answer: str


class AssessmentSubmit(BaseModel):
    user_id: str
    answers: List[QuestionAnswer]


class SkillScore(BaseModel):
    skill: str
    score: float  # 0-100 percentage
    level: SkillLevel


class AssessmentResult(BaseModel):
    user_id: str
    scores: List[SkillScore]
    total_score: float


# ============ Skills Database ============
class SkillsForRole(BaseModel):
    role: str
    skills: List[str]
    description: Optional[str] = None


# ============ Roadmap Models ============
class RoadmapMilestone(BaseModel):
    month: int
    skill: str
    reason: Optional[str] = None


class RoadmapResponse(BaseModel):
    user_id: str
    goal: str
    skills_gap: List[str]
    current_level: str
    roadmap: List[RoadmapMilestone]
    progress: dict
    explanation: Optional[str] = None


# ============ Progress Models ============
class ProgressUpdate(BaseModel):
    user_id: str
    skill: str
    completed: bool
    weeks_taken: Optional[int] = None


# ============ Agent Models ============
class MentorMessage(BaseModel):
    user_id: str
    message: str
    context: Optional[dict] = None
