"""Opt-in PostgreSQL validation using only temporary tables, never public data."""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateTable
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.settings import Database
from app.features.engagement.model import ActivityEvent
from app.features.engagement import service as engagement_service
from app.features.engagement.schemas import EngagementActivityRequest
from app.features.engagement.service import EngagementService
from app.features.lesson.model import LessonProgress
from app.features.preferences.schemas import UserPreferencesResponse
from app.main import app  # Register all foreign-key targets for PostgreSQL DDL.


@pytest.mark.skipif(os.environ.get("ENGAGEMENT_POSTGRES_TEST") != "1", reason="Opt-in local PostgreSQL test")
@pytest.mark.asyncio
async def test_postgresql_time_aggregation_and_deduplication(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 5, 17, 30, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr("app.features.engagement.service.datetime", FixedDateTime)
    monkeypatch.setattr(
        "app.features.engagement.service.UserPreferencesService.get_preferences",
        AsyncMock(return_value=UserPreferencesResponse(user_id=7)),
    )
    engine = create_async_engine(Database().sqlalchemy_async_database_uri)
    try:
        async with engine.begin() as connection:
            # Temp tables shadow public tables on this connection and disappear on commit.
            for name in ("User", "Lesson", "Vocabulary", "LessonSession", "Conversation"):
                await connection.execute(text(
                    f'CREATE TEMPORARY TABLE "{name}" (id INTEGER PRIMARY KEY) ON COMMIT DROP'
                ))
            await connection.execute(text('INSERT INTO pg_temp."User" (id) VALUES (7), (8)'))
            for model in (ActivityEvent, LessonProgress):
                ddl = str(CreateTable(model.__table__).compile(dialect=engine.dialect))
                ddl = ddl.replace("CREATE TABLE", "CREATE TEMPORARY TABLE", 1)
                await connection.execute(text(ddl + " ON COMMIT DROP"))
            async with AsyncSession(bind=connection) as session:
                data = EngagementActivityRequest(
                    event_id=uuid4(), activity_type="listening", duration_seconds=120,
                )
                first = await EngagementService.record_activity(7, data, session)
                original_get = engagement_service.async_get_one_record_by
                calls = 0

                async def miss_initial_lookup(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 1:
                        return None
                    return await original_get(*args, **kwargs)

                monkeypatch.setattr(
                    engagement_service,
                    "async_get_one_record_by",
                    miss_initial_lookup,
                )
                retry = await EngagementService.record_activity(7, data, session)
                assert first == retry
                assert calls == 2
                monkeypatch.setattr(
                    engagement_service, "async_get_one_record_by", original_get
                )
                await EngagementService.record_activity(7, EngagementActivityRequest(
                    event_id=uuid4(), activity_type="vocabulary", duration_seconds=30,
                ), session)
                await EngagementService.record_activity(8, data, session)
                summary = await EngagementService.get_summary(7, session)
                assert summary.today.date.isoformat() == "2026-10-06"
                assert summary.today.learned_seconds == 150
                assert summary.today.vocabulary_seconds == 30
                assert summary.current_streak == 1
                history = await EngagementService.get_activity(7, 90, session)
                assert history.total_seconds == 150
                assert len(history.data) == 90
    finally:
        await engine.dispose()
