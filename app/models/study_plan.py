from pydantic import BaseModel
from typing import List, Dict, Optional, Literal, Union
from datetime import date, datetime, time


class Topic(BaseModel):
    name: str
    estimated_hours: float
    difficulty: Optional[int] = 3  # 1-5 scale
    completed: Optional[bool] = False


class Subject(BaseModel):
    id: Optional[int] = None
    name: str
    topics: List[Topic]
    exam_date: Optional[date] = None
    importance: Literal["High", "Medium", "Low"] = "Medium"
    difficulty: Optional[int] = 3  # 1-5 scale


class StudySession(BaseModel):
    subject: str
    topic: str
    date: date
    start_time: time
    end_time: time
    duration_hours: float
    session_type: Optional[str] = "regular"  # regular, revision


class StudyDay(BaseModel):
    date: date
    sessions: List[StudySession]


class TimeBlock(BaseModel):
    start_hour: int
    end_hour: int
    days: List[str]  # days of week this block applies to


class UserProfile(BaseModel):
    name: Optional[str] = None
    level: Optional[str] = None


class StudyPreferences(BaseModel):
    weekday_hours: float = 3.0
    weekend_hours: float = 5.0
    time_blocks: Optional[List[TimeBlock]] = None
    study_style: Optional[Literal["fixed", "flexible"]] = "flexible"
    session_length: Optional[Literal["long", "pomodoro"]] = "long"
    break_duration: float = 0.25  # hours
    session_duration: float = 1.5  # hours
    revision_days_before: int = 2
    weekly_revision: bool = False
    break_days: Optional[List[date]] = None


class StudyPlanRequest(BaseModel):
    user_profile: Optional[UserProfile] = None
    subjects: List[Subject]
    start_date: date
    end_date: date
    preferences: StudyPreferences


class StudyPlanResponse(BaseModel):
    days: List[StudyDay]
    total_study_hours: float
    subjects_distribution: Dict[str, float]  # subject -> hours
    insufficient_time: Optional[bool] = False
    total_hours_needed: Optional[float] = None
    available_hours: Optional[float] = None
    unallocated_topics: Optional[List[Dict[str, Union[str, float]]]] = None 