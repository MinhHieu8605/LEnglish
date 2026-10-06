from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


EngagementActivityType = Literal["listening", "vocabulary"]


class EngagementActivityRequest(BaseModel):
    """
    A small batch of active study time; reuse event_id when retrying.

    Attributes:
        event_id (UUID): The client-provided event identifier reused when retrying an
            activity report.
        activity_type (EngagementActivityType): Whether the activity records listening
            or vocabulary study.
        duration_seconds (int): The duration of the video or activity in seconds.
    """

    event_id: UUID
    activity_type: EngagementActivityType
    duration_seconds: int = Field(..., ge=1, le=300, strict=True)


class EngagementActivityResponse(BaseModel):
    """
    A recorded batch, including its original timestamp on retries.

    Attributes:
        event_id (UUID): The client-provided event identifier reused when retrying an
            activity report.
        activity_type (EngagementActivityType): Whether the activity records listening
            or vocabulary study.
        duration_seconds (int): The duration of the video or activity in seconds.
        recorded_at (datetime): The original event timestamp, retained when the same
            event is retried.
    """

    event_id: UUID
    activity_type: EngagementActivityType
    duration_seconds: int
    recorded_at: datetime


class EngagementTodayResponse(BaseModel):
    """
    Active study time for the current local calendar day.

    Attributes:
        date (date): The local calendar date represented by the activity totals.
        learned_seconds (int): The combined listening and vocabulary study time in
            seconds.
        learned_minutes (float): The combined active study time expressed in minutes.
        listening_seconds (int): The listening study time in seconds.
        vocabulary_seconds (int): The vocabulary study time in seconds.
    """

    date: date
    learned_seconds: int
    learned_minutes: float
    listening_seconds: int
    vocabulary_seconds: int


class EngagementSummaryResponse(BaseModel):
    """
    Daily goal progress, completed lessons, and lifetime learning streaks.

    Attributes:
        timezone (str): The user's IANA timezone used for local dates and learning
            statistics.
        today (EngagementTodayResponse): The study totals for the current local calendar
            day.
        daily_goal_minutes (int): The user's daily target for active study time in
            minutes.
        goal_progress_percent (float): The percentage of today's learning goal
            completed.
        remaining_minutes (int): The minutes still needed to reach today's learning
            goal.
        completed_lessons (int): The user's total number of completed lesson progress
            records.
        current_streak (int): The consecutive active days ending today or yesterday.
        longest_streak (int): The longest sequence of consecutive active days in the
            user's history.
        last_active_date (Optional[date]): The most recent local date with recorded
            study activity, if any.
    """

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
    """
    One heatmap day with study time separated by activity type.

    Attributes:
        date (date): The local calendar date represented by the activity totals.
        learned_seconds (int): The combined listening and vocabulary study time in
            seconds.
        minutes (float): The active study time for this day expressed in minutes.
        listening_seconds (int): The listening study time in seconds.
        vocabulary_seconds (int): The vocabulary study time in seconds.
        intensity (int): The heatmap level derived from this day's study time and daily
            goal.
    """

    date: date
    learned_seconds: int
    minutes: float
    listening_seconds: int
    vocabulary_seconds: int
    intensity: int


class EngagementActivityHistoryResponse(BaseModel):
    """
    A complete heatmap range and the learning totals within it.

    Attributes:
        timezone (str): The user's IANA timezone used for local dates and learning
            statistics.
        start_date (date): The first local date included in the activity history.
        end_date (date): The last local date included in the activity history.
        days (int): The number of calendar days included in the history window.
        data (List[EngagementDayResponse]): The ordered items included in the response.
        today (EngagementTodayResponse): The study totals for the current local calendar
            day.
        active_days (int): The number of days with positive study time in the history
            window.
        total_seconds (int): The total active study time in the history window, in
            seconds.
        total_minutes (float): The total active study time in the history window, in
            minutes.
        current_streak (int): The consecutive active days ending today or yesterday.
        longest_streak (int): The longest sequence of consecutive active days in the
            user's history.
    """

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
