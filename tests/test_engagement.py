from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB, dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.engagement.model import ActivityEvent
from app.features.engagement import service as engagement_service
from app.features.engagement.service import _streaks
from app.features.lesson.model import LessonProgress
from app.features.preferences.schemas import UserPreferencesResponse
from app.main import app
from app.middleware.auth import get_current_user


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, compiler, **kwargs):
    return "JSON"


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 5, 17, 30, tzinfo=timezone.utc).astimezone(tz)


class EngagementSession(AsyncSession):
    def __init__(self, sync_session):
        super().__init__()
        self.sync = sync_session

    async def exec(self, statement):
        statement.compile(dialect=dialect())
        return self.sync.exec(statement)

    def in_transaction(self):
        return self.sync.in_transaction()

    def add(self, record):
        self.sync.add(record)

    async def flush(self):
        self.sync.flush()

    async def refresh(self, record, attribute_names=None):
        self.sync.refresh(record, attribute_names)

    @asynccontextmanager
    async def begin(self):
        with self.sync.begin():
            yield

    @asynccontextmanager
    async def begin_nested(self):
        with self.sync.begin_nested():
            yield

    async def commit(self):
        self.sync.commit()

    async def rollback(self):
        self.sync.rollback()


@pytest.fixture
def engagement_session(monkeypatch):
    monkeypatch.setattr("app.features.engagement.service.datetime", FixedDateTime)
    monkeypatch.setattr(
        "app.features.engagement.service.UserPreferencesService.get_preferences",
        AsyncMock(return_value=UserPreferencesResponse(user_id=7, daily_goal_minutes=20)),
    )
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def timezone_function(connection, _record):
        def local_time(zone, value):
            utc = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            return utc.astimezone(ZoneInfo(zone)).replace(tzinfo=None).isoformat()
        connection.create_function("timezone", 2, local_time)

    try:
        ActivityEvent.__table__.create(engine)
        LessonProgress.__table__.create(engine)
        with Session(engine) as sync:
            yield EngagementSession(sync)
    finally:
        engine.dispose()


@pytest.fixture
def engagement_client(engagement_session):
    async def session_override():
        yield engagement_session

    async def user_override(request: Request):
        request.state.user_id = 7
        request.state.role = "user"

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_user, None)


def seed_activity(session, when, seconds=60, activity_type="listening", user_id=7, **values):
    session.sync.add(ActivityEvent(
        user_id=user_id, event_id=str(uuid4()), type=activity_type,
        duration_seconds=seconds, created_time=when, **values,
    ))
    session.sync.commit()


def test_empty_home_returns_zero_summary_and_complete_90_day_range(engagement_client):
    summary = engagement_client.get("/api/v1/engagement/summary").json()
    assert summary["today"] == {
        "date": "2026-10-06", "learned_seconds": 0, "learned_minutes": 0,
        "listening_seconds": 0, "vocabulary_seconds": 0,
    }
    assert summary["daily_goal_minutes"] == 20
    assert summary["remaining_minutes"] == 20
    assert summary["completed_lessons"] == 0
    assert summary["current_streak"] == summary["longest_streak"] == 0
    assert summary["last_active_date"] is None
    history = engagement_client.get("/api/v1/engagement/activity").json()
    assert history["start_date"] == "2026-07-09"
    assert history["end_date"] == "2026-10-06"
    assert history["days"] == len(history["data"]) == 90
    assert all(day["learned_seconds"] == day["intensity"] == 0 for day in history["data"])


def test_post_retries_do_not_add_time_and_payload_conflicts_return_409(engagement_client, engagement_session):
    payload = {"event_id": str(uuid4()), "activity_type": "listening", "duration_seconds": 120}
    first = engagement_client.post("/api/v1/engagement/activity", json=payload)
    retry = engagement_client.post("/api/v1/engagement/activity", json=payload)
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert first.json()["recorded_at"] == "2026-10-05T17:30:00Z"
    for changed in ({"duration_seconds": 121}, {"activity_type": "vocabulary"}):
        assert engagement_client.post("/api/v1/engagement/activity", json={**payload, **changed}).status_code == 409
    engagement_client.post("/api/v1/engagement/activity", json={
        "event_id": str(uuid4()), "activity_type": "vocabulary", "duration_seconds": 30,
    })
    summary = engagement_client.get("/api/v1/engagement/summary").json()
    assert summary["today"]["learned_seconds"] == 150
    assert summary["today"]["learned_minutes"] == 2.5
    assert summary["today"]["vocabulary_seconds"] == 30
    assert summary["goal_progress_percent"] == 12.5
    assert summary["remaining_minutes"] == 18
    assert summary["current_streak"] == 1
    assert len(engagement_session.sync.exec(select(ActivityEvent)).all()) == 2


def test_retry_collision_rolls_back_savepoint_and_keeps_transaction_usable(
    engagement_client, engagement_session, monkeypatch,
):
    payload = {
        "event_id": str(uuid4()),
        "activity_type": "listening",
        "duration_seconds": 120,
    }
    first = engagement_client.post("/api/v1/engagement/activity", json=payload)
    original_get = engagement_service.async_get_one_record_by
    calls = 0

    async def miss_initial_lookup(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return await original_get(*args, **kwargs)

    # Reproduce a retry inserted by another request after the initial lookup.
    monkeypatch.setattr(
        engagement_service, "async_get_one_record_by", miss_initial_lookup
    )
    retry = engagement_client.post("/api/v1/engagement/activity", json=payload)
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert calls == 2
    assert len(engagement_session.sync.exec(select(ActivityEvent)).all()) == 1
    next_batch = engagement_client.post("/api/v1/engagement/activity", json={
        **payload,
        "event_id": str(uuid4()),
    })
    assert next_batch.status_code == 200
    assert engagement_client.get("/api/v1/engagement/summary").json()["today"]["learned_seconds"] == 240


@pytest.mark.parametrize("changed", [
    {"duration_seconds": 0}, {"duration_seconds": -1}, {"duration_seconds": 301},
    {"duration_seconds": 1.5}, {"duration_seconds": True},
    {"activity_type": "idle"}, {"event_id": "invalid"},
])
def test_invalid_activity_is_rejected(engagement_client, changed):
    response = engagement_client.post("/api/v1/engagement/activity", json={
        "event_id": str(uuid4()), "activity_type": "listening", "duration_seconds": 60,
        **changed,
    })
    assert response.status_code == 422


@pytest.mark.parametrize("days", [0, -1, 367])
def test_invalid_history_window_is_rejected(engagement_client, days):
    assert engagement_client.get("/api/v1/engagement/activity", params={"days": days}).status_code == 422


def test_timezone_boundaries_user_isolation_and_completion_count(engagement_client, engagement_session):
    midnight = datetime(2026, 10, 5, 17, tzinfo=timezone.utc)
    seed_activity(engagement_session, midnight - timedelta(seconds=1), seconds=180)
    seed_activity(engagement_session, midnight, seconds=240)
    seed_activity(engagement_session, midnight + timedelta(minutes=1), seconds=60, activity_type="vocabulary")
    seed_activity(engagement_session, midnight, seconds=300, user_id=8)
    seed_activity(engagement_session, midnight, seconds=300, activity_type="lookup")
    seed_activity(engagement_session, midnight + timedelta(days=1), seconds=300)
    for lesson_id, user_id, completed_at in (
        (1, 7, midnight), (2, 7, None), (3, 8, midnight),
    ):
        engagement_session.sync.add(LessonProgress(
            lesson_id=lesson_id, user_id=user_id, completed_at=completed_at,
        ))
    engagement_session.sync.commit()
    summary = engagement_client.get("/api/v1/engagement/summary").json()
    assert summary["today"]["learned_seconds"] == 300
    assert summary["completed_lessons"] == 1
    assert summary["current_streak"] == summary["longest_streak"] == 2
    history = engagement_client.get("/api/v1/engagement/activity", params={"days": 3}).json()
    assert [day["learned_seconds"] for day in history["data"]] == [0, 180, 300]
    assert history["active_days"] == 2
    assert history["total_seconds"] == 480
    assert history["total_minutes"] == 8


def test_other_timezone_and_goal_overflow(engagement_client, engagement_session, monkeypatch):
    monkeypatch.setattr(
        "app.features.engagement.service.UserPreferencesService.get_preferences",
        AsyncMock(return_value=UserPreferencesResponse(user_id=7, daily_goal_minutes=1, timezone="UTC")),
    )
    seed_activity(engagement_session, datetime(2026, 10, 5, 17, tzinfo=timezone.utc), seconds=90)
    summary = engagement_client.get("/api/v1/engagement/summary").json()
    assert summary["today"]["date"] == "2026-10-05"
    assert summary["goal_progress_percent"] == 100
    assert summary["remaining_minutes"] == 0


def test_same_event_id_can_be_used_by_different_users(engagement_client, engagement_session):
    event_id = str(uuid4())
    engagement_session.sync.add(ActivityEvent(
        user_id=8, event_id=event_id, type="listening", duration_seconds=30,
        created_time=datetime(2026, 10, 5, 17, tzinfo=timezone.utc),
    ))
    engagement_session.sync.commit()
    response = engagement_client.post("/api/v1/engagement/activity", json={
        "event_id": event_id, "activity_type": "vocabulary", "duration_seconds": 60,
    })
    assert response.status_code == 200
    assert engagement_client.get("/api/v1/engagement/summary").json()["today"]["learned_seconds"] == 60


def test_period_totals_exclude_old_days_but_current_streak_uses_full_history(engagement_client, engagement_session):
    for day in range(1, 7):
        seed_activity(engagement_session, datetime(2026, 10, day, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")).astimezone(timezone.utc))
    history = engagement_client.get("/api/v1/engagement/activity", params={"days": 2}).json()
    assert history["total_seconds"] == 120
    assert history["active_days"] == history["longest_streak"] == 2
    assert history["current_streak"] == 6
    assert engagement_client.get("/api/v1/engagement/summary").json()["longest_streak"] == 6


@pytest.mark.parametrize(("offsets", "current", "longest"), [
    ([], 0, 0), ([-5, -4, -3], 0, 3), ([-3, -2, -1], 3, 3),
    ([-4, -3, -1, 0], 2, 2), ([-1], 1, 1), ([0], 1, 1),
])
def test_streak_handles_gaps_and_yesterday(offsets, current, longest):
    today = datetime(2026, 10, 6).date()
    assert _streaks([today + timedelta(days=offset) for offset in offsets], today) == (current, longest)


def test_engagement_endpoints_require_authentication():
    with TestClient(app) as client:
        for path in ("/api/v1/engagement/summary", "/api/v1/engagement/activity"):
            assert client.get(path).status_code == 401
        assert client.post("/api/v1/engagement/activity", json={
            "event_id": str(uuid4()), "activity_type": "listening", "duration_seconds": 60,
        }).status_code == 401
