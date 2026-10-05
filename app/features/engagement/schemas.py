from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


EngagementActivityType = Literal["listening", "vocabulary"]


class EngagementActivityRequest(BaseModel):
    """A small batch of active study time; reuse event_id when retrying."""

    event_id: UUID
    activity_type: EngagementActivityType
    duration_seconds: int = Field(..., ge=1, le=300, strict=True)


class EngagementActivityResponse(BaseModel):
    """A recorded batch, including its original timestamp on retries."""

    event_id: UUID
    activity_type: EngagementActivityType
    duration_seconds: int
    recorded_at: datetime


class EngagementTodayResponse(BaseModel):
    """Active study time for the current local calendar day."""

    date: date
    learned_seconds: int
    learned_minutes: float
    listening_seconds: int
    vocabulary_seconds: int


class EngagementSummaryResponse(BaseModel):
    """Daily goal progress, completed lessons, and lifetime learning streaks."""

    timezone: str
    today: EngagementTodayResponse
    daily_goal_minutes: int
    goal_progress_percent: float
    remaining_minutes: int
    completed_lessons: int
    current_streak: int
    longest_streak: int
    last_active_date: Optional[date]


class EngagementDayResponse(BaseModel):
    """One heatmap day with study time separated by activity type."""

    date: date
    learned_seconds: int
    minutes: float
    listening_seconds: int
    vocabulary_seconds: int
    intensity: int


class EngagementActivityHistoryResponse(BaseModel):
    """A complete heatmap range and the learning totals within it."""

    timezone: str
    start_date: date
    end_date: date
    days: int
    data: List[EngagementDayResponse]
    today: EngagementTodayResponse
    active_days: int
    total_seconds: int
    total_minutes: float
    current_streak: int
    longest_streak: int
