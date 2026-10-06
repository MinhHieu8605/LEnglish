import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import Date, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_record,
    async_get_one_record_by,
    transactional,
)
from app.features.engagement.model import ActivityEvent
from app.features.engagement.schemas import (
    EngagementActivityHistoryResponse,
    EngagementActivityRequest,
    EngagementActivityResponse,
    EngagementDayResponse,
    EngagementSummaryResponse,
    EngagementTodayResponse,
)
from app.features.lesson.model import LessonProgress
from app.features.preferences.service import UserPreferencesService


def _streaks(active_dates: list[date], today: date) -> tuple[int, int]:
    """
    Calculate the current and longest learning streak.

    Args:
        active_dates (list[date]): The local dates with positive study activity.
        today (date): The local calendar date used to determine the current streak.

    Returns:
        tuple[int, int]: The current streak and the longest streak, measured in
            consecutive days.
    """
    current = 0
    longest = 0
    run = 0
    previous = None

    for day in sorted(active_dates):
        if previous == day - timedelta(days=1):
            run += 1
        else:
            run = 1

        longest = max(longest, run)

        if day in (today, today - timedelta(days=1)):
            current = run

        previous = day

    return current, longest


async def _get_daily_activity(
    user_id: int,
    user_timezone: str,
    now: datetime,
    session: AsyncSession,
) -> dict[date, tuple[int, int]]:
    """
    Load daily listening and vocabulary totals for one user.

    Args:
        user_id (int): The identifier of the user whose records are requested.
        user_timezone (str): The IANA timezone used to group activity into local
            calendar days.
        now (datetime): The current timestamp used to exclude future activity or
            classify review progress.
        session (AsyncSession): The database session used for record operations.

    Returns:
        dict[date, tuple[int, int]]: Local dates mapped to listening and vocabulary
            totals in seconds.
    """
    local_date = func.date(
        func.timezone(user_timezone, ActivityEvent.created_time),
        type_=Date,
    )

    result = await session.exec(
        select(
            local_date,
            ActivityEvent.type,
            func.sum(ActivityEvent.duration_seconds),
        )
        .where(
            ActivityEvent.user_id == user_id,
            ActivityEvent.type.in_(["listening", "vocabulary"]),
            ActivityEvent.event_id.is_not(None),
            ActivityEvent.duration_seconds > 0,
            ActivityEvent.created_time <= now,
        )
        .group_by(local_date, ActivityEvent.type)
    )

    daily: dict[date, tuple[int, int]] = {}

    for day, activity_type, seconds in result.all():
        listening, vocabulary = daily.get(day, (0, 0))

        if activity_type == "listening":
            listening += seconds
        else:
            vocabulary += seconds

        daily[day] = (listening, vocabulary)

    return daily


class EngagementService(object):
    """
    Record active-time batches and aggregate them in the user's timezone.

    Stores study batches, summarizes learning goals and streaks, and builds complete
    activity histories.
    """

    @staticmethod
    @transactional()
    async def record_activity(
        user_id: int,
        data: EngagementActivityRequest,
        session: AsyncSession,
    ) -> EngagementActivityResponse:
        """
        Record active study time without counting a retried batch twice.

        Args:
            user_id (int): Identifier of the authenticated user.
            data (EngagementActivityRequest): Activity batch and retry identifier.
            session (AsyncSession): Active database session.

        Returns:
            EngagementActivityResponse: The original recorded batch.

        Raises:
            HTTPException: If the event identifier is reused with different data.
        """
        event = await async_get_one_record_by(
            ActivityEvent,
            [
                ActivityEvent.user_id == user_id,
                ActivityEvent.event_id == str(data.event_id),
            ],
            session,
            raise_if_not_found=False,
        )

        if event is None:
            now = datetime.now(timezone.utc)

            event = await async_create_record(
                ActivityEvent,
                {
                    "user_id": user_id,
                    "event_id": str(data.event_id),
                    "type": data.activity_type,
                    "duration_seconds": data.duration_seconds,
                    "created_time": now,
                    "updated_time": now,
                },
                session,
            )

        if (
            event.type != data.activity_type
            or event.duration_seconds != data.duration_seconds
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event ID already used for different activity",
            )

        recorded_at = event.created_time

        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)

        return EngagementActivityResponse(
            event_id=data.event_id,
            activity_type=event.type,
            duration_seconds=event.duration_seconds,
            recorded_at=recorded_at,
        )

    @staticmethod
    async def get_summary(
        user_id: int,
        session: AsyncSession,
    ) -> EngagementSummaryResponse:
        """
        Return today's learning goal, completed lessons, and lifetime streaks.

        Args:
            user_id (int): Identifier of the authenticated user.
            session (AsyncSession): Active database session.

        Returns:
            EngagementSummaryResponse: Engagement totals in the user's timezone.
        """
        preferences = await UserPreferencesService.get_preferences(
            user_id,
            session,
        )

        now = datetime.now(timezone.utc)
        today = now.astimezone(ZoneInfo(preferences.timezone)).date()

        daily = await _get_daily_activity(
            user_id,
            preferences.timezone,
            now,
            session,
        )

        listening, vocabulary = daily.get(today, (0, 0))
        learned_seconds = listening + vocabulary

        today_activity = EngagementTodayResponse(
            date=today,
            learned_seconds=learned_seconds,
            learned_minutes=round(learned_seconds / 60, 2),
            listening_seconds=listening,
            vocabulary_seconds=vocabulary,
        )

        current_streak, longest_streak = _streaks(
            list(daily),
            today,
        )

        completed_lessons = (
            await session.exec(
                select(func.count(LessonProgress.id)).where(
                    LessonProgress.user_id == user_id,
                    LessonProgress.completed_at.is_not(None),
                    LessonProgress.completed_at <= now,
                )
            )
        ).one()

        goal_seconds = preferences.daily_goal_minutes * 60

        return EngagementSummaryResponse(
            timezone=preferences.timezone,
            today=today_activity,
            daily_goal_minutes=preferences.daily_goal_minutes,
            goal_progress_percent=round(
                min(100, learned_seconds / goal_seconds * 100),
                2,
            ),
            remaining_minutes=math.ceil(
                max(0, goal_seconds - learned_seconds) / 60
            ),
            completed_lessons=completed_lessons,
            current_streak=current_streak,
            longest_streak=longest_streak,
            last_active_date=max(daily, default=None),
        )

    @staticmethod
    async def get_activity(
        user_id: int,
        days: int,
        session: AsyncSession,
    ) -> EngagementActivityHistoryResponse:
        """
        Return a complete daily heatmap and totals for the requested period.

        Args:
            user_id (int): Identifier of the authenticated user.
            days (int): Number of local calendar days, including today.
            session (AsyncSession): Active database session.

        Returns:
            EngagementActivityHistoryResponse: Daily activity and period totals.
        """
        preferences = await UserPreferencesService.get_preferences(
            user_id,
            session,
        )

        now = datetime.now(timezone.utc)
        today = now.astimezone(ZoneInfo(preferences.timezone)).date()
        start = today - timedelta(days=days - 1)

        daily = await _get_daily_activity(
            user_id,
            preferences.timezone,
            now,
            session,
        )

        data = []

        for offset in range(days):
            day = start + timedelta(days=offset)
            listening, vocabulary = daily.get(day, (0, 0))
            seconds = listening + vocabulary

            if seconds == 0:
                intensity = 0
            elif seconds < 900:
                intensity = 1
            elif seconds < 1320:
                intensity = 2
            elif seconds < 1800:
                intensity = 3
            else:
                intensity = 4

            data.append(
                EngagementDayResponse(
                    date=day,
                    learned_seconds=seconds,
                    minutes=round(seconds / 60, 2),
                    listening_seconds=listening,
                    vocabulary_seconds=vocabulary,
                    intensity=intensity,
                )
            )

        active_dates = [
            item.date
            for item in data
            if item.learned_seconds > 0
        ]

        current_streak, _ = _streaks(list(daily), today)
        _, longest_streak = _streaks(active_dates, today)

        total_seconds = sum(
            item.learned_seconds
            for item in data
        )

        today_listening, today_vocabulary = daily.get(today, (0, 0))
        today_seconds = today_listening + today_vocabulary

        return EngagementActivityHistoryResponse(
            timezone=preferences.timezone,
            start_date=start,
            end_date=today,
            days=days,
            data=data,
            today=EngagementTodayResponse(
                date=today,
                learned_seconds=today_seconds,
                learned_minutes=round(today_seconds / 60, 2),
                listening_seconds=today_listening,
                vocabulary_seconds=today_vocabulary,
            ),
            active_days=len(active_dates),
            total_seconds=total_seconds,
            total_minutes=round(total_seconds / 60, 2),
            current_streak=current_streak,
            longest_streak=longest_streak,
        )
