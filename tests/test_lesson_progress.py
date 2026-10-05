from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from fastapi import Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import raiseload
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.lesson.model import Category, Lesson, LessonProgress, Subtitle
from app.features.lesson.youtube import TranscriptSegment, YouTubeLessonSource
from app.main import app
from app.middleware.auth import get_current_user


class ProgressSession(AsyncSession):
    """Run real SQL and transaction boundaries against an isolated SQLite database."""

    def __init__(self, sync_session):
        super().__init__()
        self.test_session = sync_session

    async def exec(self, statement):
        statement.compile(dialect=postgresql.dialect())
        return self.test_session.exec(statement.options(raiseload("*")))

    async def get(self, model, record_id, **kwargs):
        return self.test_session.get(model, record_id, **kwargs)

    def add(self, record):
        self.test_session.add(record)

    def in_transaction(self):
        return self.test_session.in_transaction()

    @asynccontextmanager
    async def begin(self):
        with self.test_session.begin():
            yield

    @asynccontextmanager
    async def begin_nested(self):
        with self.test_session.begin_nested():
            yield

    async def flush(self):
        self.test_session.flush()

    async def commit(self):
        self.test_session.commit()

    async def rollback(self):
        self.test_session.rollback()

    async def refresh(self, record, attribute_names=None):
        self.test_session.refresh(record, attribute_names)


@pytest.fixture
def progress_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    try:
        for model in (Category, Lesson, Subtitle, LessonProgress):
            model.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(Category.__table__.insert(), {
                "id": 1, "name": "Work", "slug": "work",
            })
            for lesson_id in range(1, 7):
                connection.execute(Lesson.__table__.insert(), {
                    "id": lesson_id, "title": f"Lesson {lesson_id}",
                    "slug": f"lesson-{lesson_id}", "video_id": f"video-{lesson_id}",
                    "difficulty": "B1", "duration_seconds": 30,
                    "status": "draft" if lesson_id == 4 else "published",
                    "category_id": 1 if lesson_id == 1 else None,
                    "channel_name": "TED" if lesson_id == 1 else None,
                })
            connection.execute(Subtitle.__table__.insert(), [
                {"id": 11, "lesson_id": 1, "sequence": 1, "start_ms": 2000,
                 "end_ms": 5000, "content_en": "Hello."},
                {"id": 12, "lesson_id": 1, "sequence": 2, "start_ms": 8000,
                 "end_ms": 12000, "content_en": "Goodbye."},
            ])
        with Session(engine) as sync_session:
            yield ProgressSession(sync_session)
    finally:
        engine.dispose()


@pytest.fixture
def progress_client(progress_session):
    async def session_override():
        yield progress_session

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


def seed_progress(progress_session, lesson_id=1, user_id=7, day=1, **values):
    progress_session.test_session.add(LessonProgress(
        lesson_id=lesson_id, user_id=user_id, last_position_seconds=9,
        last_watched_at=datetime(2026, 10, day, tzinfo=timezone.utc), **values,
    ))
    progress_session.test_session.commit()


def test_unstarted_progress_returns_first_sentence_and_no_resume(progress_client):
    response = progress_client.get("/api/v1/lessons/lesson-1/progress")
    assert response.status_code == 200
    progress = response.json()
    assert progress["last_position_seconds"] == 0
    assert progress["last_watched_at"] is None
    assert progress["subtitle_count"] == 2
    assert progress["current_subtitle"]["id"] == 11
    response = progress_client.get("/api/v1/lessons/resume")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.parametrize(("position", "subtitle_id"), [
    (0, 11), (2, 11), (4, 11), (5, 12), (7, 12), (8, 12), (11, 12),
    (12, None), (29, None), (30, None),
])
def test_saved_position_round_trips_with_sentence_boundaries(
    progress_client, position, subtitle_id,
):
    response = progress_client.put("/api/v1/lessons/lesson-1/progress", json={
        "last_position_seconds": position,
    })
    assert response.status_code == 200
    saved = response.json()
    assert saved["last_position_seconds"] == position
    assert saved["last_watched_at"] is not None
    assert saved["subtitle_count"] == 2
    subtitle = saved["current_subtitle"]
    assert (subtitle["id"] if subtitle else None) == subtitle_id
    fetched = progress_client.get("/api/v1/lessons/lesson-1/progress").json()
    assert fetched == saved
    # Exercise updating an existing progress row as well as creating one.
    assert progress_client.put("/api/v1/lessons/lesson-1/progress", json={
        "last_position_seconds": position,
    }).status_code == 200
    resume = progress_client.get("/api/v1/lessons/resume").json()
    if position == 30:
        assert saved["completed_at"] is not None
        assert resume is None
    else:
        assert resume["lesson"]["slug"] == "lesson-1"
        assert resume["progress"]["current_subtitle"] == subtitle


def test_resume_selects_latest_eligible_progress_for_current_user(
    progress_client, progress_session,
):
    seed_progress(progress_session, lesson_id=2, day=1)
    seed_progress(progress_session, lesson_id=1, day=2, completion_percent=30)
    seed_progress(progress_session, lesson_id=3, day=3, completion_percent=100)
    seed_progress(progress_session, lesson_id=4, day=4)
    seed_progress(progress_session, lesson_id=5, day=5,
                  completed_at=datetime(2026, 10, 5, tzinfo=timezone.utc))
    seed_progress(progress_session, lesson_id=6, user_id=8, day=6)
    progress_session.test_session.add(LessonProgress(user_id=7, lesson_id=6))
    progress_session.test_session.commit()
    response = progress_client.get("/api/v1/lessons/resume")
    assert response.status_code == 200
    result = response.json()
    assert result["lesson"]["id"] == 1
    assert result["lesson"]["channel_name"] == "TED"
    assert result["lesson"]["topic"] == "Work"
    assert result["lesson"]["subtitle_count"] == 2
    assert result["progress"]["current_subtitle"]["sequence"] == 2
    assert result["progress"]["current_subtitle"]["content_en"] == "Goodbye."


def test_resume_ties_are_stable_and_support_lessons_without_subtitles(
    progress_client, progress_session,
):
    seed_progress(progress_session, lesson_id=1)
    seed_progress(progress_session, lesson_id=2)
    for _ in range(2):
        result = progress_client.get("/api/v1/lessons/resume").json()
        assert result["lesson"]["id"] == 2
        assert result["lesson"]["topic"] is None
        assert result["progress"]["subtitle_count"] == 0
        assert result["progress"]["current_subtitle"] is None


def test_progress_does_not_expose_another_users_position(progress_client, progress_session):
    seed_progress(progress_session, user_id=8)
    progress = progress_client.get("/api/v1/lessons/lesson-1/progress").json()
    assert progress["last_position_seconds"] == 0
    assert progress["current_subtitle"]["id"] == 11
    assert progress_client.get("/api/v1/lessons/resume").json() is None


@pytest.mark.parametrize("slug", ["missing", "lesson-4"])
def test_progress_requires_a_published_lesson(progress_client, slug):
    assert progress_client.get(f"/api/v1/lessons/{slug}/progress").status_code == 404


@pytest.mark.parametrize("position", [-1, 31])
def test_invalid_positions_do_not_create_resume_progress(progress_client, position):
    response = progress_client.put("/api/v1/lessons/lesson-1/progress", json={
        "last_position_seconds": position,
    })
    assert response.status_code == 422
    assert progress_client.get("/api/v1/lessons/resume").json() is None


def test_import_persists_transcript_and_rejects_duplicate_video(
    progress_client, progress_session, monkeypatch,
):
    source = YouTubeLessonSource(
        video_id="new-video",
        title="New lesson",
        thumbnail_url=None,
        channel_name="TED",
        segments=[
            TranscriptSegment(0.5, 2.5, "Hello.", "Xin chào."),
            TranscriptSegment(3.0, 3.0, "Goodbye.", "Tạm biệt."),
        ],
    )
    monkeypatch.setattr(
        "app.features.lesson.service.load_youtube_lesson_source",
        AsyncMock(return_value=source),
    )

    async def admin_override(request: Request):
        request.state.user_id = 7
        request.state.role = "admin"

    monkeypatch.setitem(
        app.dependency_overrides, get_current_user, admin_override
    )
    payload = {
        "video_url": "https://youtu.be/new-video",
        "category_id": 1,
        "translate_to_vi": False,
    }
    response = progress_client.post("/api/v1/lessons/import/youtube", json=payload)
    assert response.status_code == 201
    result = response.json()
    assert result["title"] == "New lesson"
    assert result["duration_seconds"] == 3
    assert result["subtitle_count"] == 2
    assert result["subtitles"][0]["start_ms"] == 500
    assert result["subtitles"][0]["translation_vi"] == "Xin chào."
    assert result["subtitles"][1]["end_ms"] == 3001
    saved_lesson = progress_session.test_session.get(Lesson, result["id"])
    assert saved_lesson.channel_name == "TED"
    saved_subtitles = progress_session.test_session.exec(
        select(Subtitle).where(Subtitle.lesson_id == result["id"])
    ).all()
    assert len(saved_subtitles) == 2
    assert {subtitle.id for subtitle in saved_subtitles} == {
        subtitle["id"] for subtitle in result["subtitles"]
    }
    assert progress_client.post(
        "/api/v1/lessons/import/youtube", json=payload
    ).status_code == 409
    assert len(progress_session.test_session.exec(
        select(Subtitle).where(Subtitle.lesson_id == result["id"])
    ).all()) == 2
