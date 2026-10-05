import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from fastapi import Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import raiseload
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.database.async_db import get_session
from app.features.lesson.model import Category, Lesson, Subtitle
from app.features.lesson.schemas import LessonPaginationFilter, YouTubeLessonImportRequest
from app.features.lesson.service import LessonService
from app.features.lesson.youtube import load_youtube_lesson_source
from app.main import app  # Load models referenced by foreign keys and relationships.
from app.middleware.auth import get_current_user


@pytest.fixture
def catalog_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    try:
        for model in (Category, Lesson, Subtitle):
            model.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(Category.__table__.insert(), [
                {"id": 1, "name": "Work", "slug": "work"},
                {"id": 2, "name": "Communication", "slug": "communication"},
            ])
            for lesson_id, title, channel, category, views, day, content_status in [
                (1, "Learning English", "TED", 1, 10, 3, "published"),
                (2, "Speak clearly", "BBC", 2, 50, 2, "published"),
                (3, "100%_ / focus", "TED", 1, 50, 2, "published"),
                (4, "Uncategorized lesson", None, None, 5, 4, "published"),
                (5, "Learning secret", "TED", 1, 999, 5, "draft"),
            ]:
                connection.execute(Lesson.__table__.insert(), {
                    "id": lesson_id, "title": title, "slug": f"lesson-{lesson_id}",
                    "video_id": f"video-{lesson_id}", "difficulty": "B1",
                    "channel_name": channel, "category_id": category,
                    "views_count": views, "status": content_status,
                    "published_at": datetime(2026, 10, day, tzinfo=timezone.utc),
                })
            connection.execute(Subtitle.__table__.insert(), [
                {"lesson_id": 1, "sequence": 1, "start_ms": 0, "end_ms": 1000, "content_en": "Hello."},
                {"lesson_id": 1, "sequence": 2, "start_ms": 1000, "end_ms": 2000, "content_en": "Goodbye."},
            ])

        with Session(engine) as sync_session:
            class CatalogSession:
                async def exec(self, statement):
                    statement.compile(dialect=postgresql.dialect())
                    return sync_session.exec(statement.options(raiseload("*")))

            yield CatalogSession()
    finally:
        engine.dispose()


def test_default_catalog_keeps_newest_order_and_returns_card_fields(catalog_session):
    lessons, total, pages = asyncio.run(
        LessonService.list_lessons(LessonPaginationFilter(), catalog_session)
    )
    assert [lesson.id for lesson in lessons] == [4, 1, 3, 2]
    assert (total, pages) == (4, 1)
    assert lessons[1].views_count == 10
    assert lessons[1].channel_name == "TED"
    assert lessons[1].topic == "Work"
    assert lessons[1].subtitle_count == 2
    assert lessons[0].channel_name is None
    assert lessons[0].topic is None
    assert lessons[0].subtitle_count == 0


def test_popular_catalog_has_stable_pagination(catalog_session):
    pages = []
    for page in (1, 2):
        lessons, total, page_count = asyncio.run(LessonService.list_lessons(
            LessonPaginationFilter(sort_by="views_count", page=page, page_size=2), catalog_session
        ))
        assert (total, page_count) == (4, 2)
        pages.append([lesson.id for lesson in lessons])
    assert pages == [[3, 2], [1, 4]]


@pytest.mark.parametrize(("keyword", "expected_ids"), [
    ("  sPeAk  ", [2]),
    ("ted", [3, 1]),
    ("wOrK", [3, 1]),
    ("%", [3]),
    ("_", [3]),
    ("/", [3]),
    ("missing", []),
    ("secret", []),
    ("   ", [3, 2, 1, 4]),
])
def test_search_matches_title_channel_or_topic_literally(catalog_session, keyword, expected_ids):
    lessons, total, pages = asyncio.run(LessonService.list_lessons(
        LessonPaginationFilter(keyword=keyword, sort_by="views_count"), catalog_session
    ))
    assert [lesson.id for lesson in lessons] == expected_ids
    assert total == len(expected_ids)
    assert pages == (1 if expected_ids else 0)


def test_search_count_matches_filtered_pagination(catalog_session):
    lessons, total, pages = asyncio.run(LessonService.list_lessons(
        LessonPaginationFilter(keyword="TED", sort_by="views_count", page=2, page_size=1),
        catalog_session,
    ))
    assert [lesson.id for lesson in lessons] == [1]
    assert (total, pages) == (2, 2)
    lessons, total, pages = asyncio.run(LessonService.list_lessons(
        LessonPaginationFilter(keyword="TED", page=3, page_size=1), catalog_session
    ))
    assert lessons == []
    assert (total, pages) == (2, 2)


@pytest.fixture
def catalog_client(catalog_session):
    async def session_override():
        yield catalog_session

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


def test_catalog_api_returns_filtered_cards_and_metadata(catalog_client):
    response = catalog_client.get("/api/v1/lessons", params={
        "keyword": "  ted  ", "sort_by": "views_count", "sort_order": "descend", "page_size": 1,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"] == {"total": 2, "page": 1, "page_size": 1, "pages": 2}
    assert payload["data"][0]["id"] == 3
    assert payload["data"][0]["views_count"] == 50
    assert payload["data"][0]["channel_name"] == "TED"
    assert payload["data"][0]["topic"] == "Work"


@pytest.mark.parametrize(("sort_by", "expected_ids"), [
    ("views_count", [4, 1, 3, 2]),
    ("published_at", [3, 2, 1, 4]),
])
def test_catalog_api_supports_ascending_sort(catalog_client, sort_by, expected_ids):
    response = catalog_client.get("/api/v1/lessons", params={
        "sort_by": sort_by, "sort_order": "ascend",
    })
    assert response.status_code == 200
    assert [lesson["id"] for lesson in response.json()["data"]] == expected_ids
    assert response.json()["metadata"]["total"] == 4


@pytest.mark.parametrize("params", [
    {"sort_by": "invalid"}, {"sort_order": "invalid"},
    {"keyword": "x" * 101}, {"page": 0}, {"page_size": 101},
])
def test_catalog_api_rejects_invalid_filters(catalog_client, params):
    assert catalog_client.get("/api/v1/lessons", params=params).status_code == 422


@pytest.mark.parametrize("author_name", [" TED &amp; Talks ", None])
def test_youtube_import_loads_and_persists_channel(monkeypatch, author_name):
    monkeypatch.setattr("app.features.lesson.youtube._fetch_youtube_metadata", AsyncMock(
        return_value={"title": "Test video", "author_name": author_name}
    ))
    monkeypatch.setattr("app.features.lesson.youtube._fetch_youtube_transcript", AsyncMock(
        return_value=[{"text": "Hello world.", "start": 0, "duration": 2}]
    ))
    source = asyncio.run(load_youtube_lesson_source("https://youtu.be/iISY9FgeYpU", False))
    expected = "TED & Talks" if author_name else None
    assert source.channel_name == expected
    async def create_lesson(model, values, session):
        lesson = model(id=101, **values)
        for subtitle_id, subtitle in enumerate(lesson.subtitles, start=1):
            subtitle.id = subtitle_id
        return lesson

    save_record = AsyncMock(side_effect=create_lesson)
    monkeypatch.setattr("app.features.lesson.service.async_create_record", save_record)
    monkeypatch.setattr(
        "app.features.lesson.service.async_get_one_record_by",
        AsyncMock(return_value=None),
    )
    result = asyncio.run(LessonService.import_youtube.__wrapped__(
        7,
        YouTubeLessonImportRequest(
            video_url="https://youtu.be/iISY9FgeYpU", translate_to_vi=False,
        ),
        object(),
    ))
    assert result.title == "Test video"
    assert result.subtitle_count == 1
    assert result.subtitles[0].content_en == "Hello world."
    assert save_record.await_args.args[1]["channel_name"] == expected
