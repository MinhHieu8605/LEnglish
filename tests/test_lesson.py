import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from youtube_transcript_api import RequestBlocked, TranscriptsDisabled

from app.api.v1.endpoint.lesson import delete_lesson
from app.features.lesson.service import (
    LessonService,
    _build_lesson_detail_response,
    _save_imported_lesson,
)
from app.features.lesson.youtube import (
    TranscriptSegment,
    _extract_youtube_video_id,
    _fetch_transcript,
    _fetch_youtube_transcript,
    _group_transcript,
    _translate_segments_to_vi,
)


@pytest.mark.parametrize(
    ("video_url", "expected_id"),
    [
        ("https://www.youtube.com/watch?v=iISY9FgeYpU", "iISY9FgeYpU"),
        ("https://youtu.be/iISY9FgeYpU", "iISY9FgeYpU"),
        ("https://www.youtube.com/shorts/iISY9FgeYpU", "iISY9FgeYpU"),
    ],
)
def test_extract_youtube_video_id(video_url, expected_id):
    assert _extract_youtube_video_id(video_url) == expected_id


def test_extract_youtube_video_id_rejects_other_hosts():
    with pytest.raises(ValueError, match="Only YouTube"):
        _extract_youtube_video_id("https://example.com/watch?v=iISY9FgeYpU")


def test_fetch_transcript_requests_structured_english_captions(monkeypatch):
    raw_data = [{"text": "Hello.", "start": 0.0, "duration": 1.0}]

    class FakeFetchedTranscript:
        def to_raw_data(self):
            return raw_data

    class FakeYouTubeTranscriptApi:
        def fetch(self, video_id, languages):
            assert video_id == "iISY9FgeYpU"
            assert languages == ["en", "en-US", "en-GB"]
            return FakeFetchedTranscript()

    monkeypatch.setattr(
        "app.features.lesson.youtube.YouTubeTranscriptApi",
        FakeYouTubeTranscriptApi,
    )

    assert _fetch_transcript("iISY9FgeYpU") == raw_data


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            TranscriptsDisabled("iISY9FgeYpU"),
            422,
            "Captions are disabled for this YouTube video",
        ),
        (
            RequestBlocked("iISY9FgeYpU"),
            503,
            "YouTube temporarily blocked transcript requests",
        ),
    ],
)
def test_fetch_youtube_transcript_returns_descriptive_errors(
    monkeypatch,
    error,
    expected_status,
    expected_detail,
):
    def fake_fetch_transcript(video_id):
        raise error

    monkeypatch.setattr(
        "app.features.lesson.youtube._fetch_transcript",
        fake_fetch_transcript,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_fetch_youtube_transcript("iISY9FgeYpU"))

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail


def test_group_transcript_preserves_spoken_content_and_timing():
    raw_snippets = [
        {"text": "What is the", "start": 0.0, "duration": 1.2},
        {"text": "difference?", "start": 1.2, "duration": 0.8},
        {"text": "[Music]", "start": 2.0, "duration": 1.0},
        {"text": "This is the answer.", "start": 3.0, "duration": 2.0},
    ]

    segments = _group_transcript(raw_snippets)

    assert [segment.content_en for segment in segments] == [
        "What is the difference?",
        "This is the answer.",
    ]
    assert segments[0].start_seconds == 0.0
    assert segments[0].end_seconds == 2.0
    assert segments[1].start_seconds == 3.0


def test_group_transcript_removes_inline_non_speech_cues():
    raw_snippets = [
        {
            "text": "World Cup. Put your flags [music] up in the air.",
            "start": 0.16,
            "duration": 5.119,
        },
        {
            "text": "Put your hands up in the air.",
            "start": 5.279,
            "duration": 2.0,
        },
    ]

    segments = _group_transcript(raw_snippets)

    assert [segment.content_en for segment in segments] == [
        "World Cup. Put your flags up in the air.",
        "Put your hands up in the air.",
    ]


def test_group_transcript_handles_overlapping_youtube_shorts_cues():
    raw_snippets = [
        {"text": "happy or", "start": 0.08, "duration": 2.519},
        {"text": "[Music]", "start": 2.96, "duration": 3.879},
        {"text": "sad", "start": 4.16, "duration": 8.439},
        {
            "text": "sad okay but I warn you I'll break your",
            "start": 6.839,
            "duration": 9.151,
        },
        {"text": "heart already broken", "start": 12.599, "duration": 6.471},
        {"text": "[Music]", "start": 15.99, "duration": 3.08},
    ]

    segments = _group_transcript(raw_snippets)

    assert [segment.content_en for segment in segments] == [
        "happy or sad",
        "okay but I warn you I'll break your heart already broken",
    ]
    assert segments[0].end_seconds == segments[1].start_seconds == 6.839


def test_translate_segments_to_vi_uses_ai_in_the_same_order(monkeypatch):
    async def fake_call_ai(**kwargs):
        assert '"happy or sad"' in kwargs["prompt"]
        return '["vui hay buồn", "đã tan vỡ rồi"]'

    monkeypatch.setattr("app.features.lesson.youtube.call_ai", fake_call_ai)
    segments = [
        TranscriptSegment(0.0, 2.0, "happy or sad"),
        TranscriptSegment(2.0, 4.0, "already broken"),
    ]

    translated = asyncio.run(_translate_segments_to_vi(segments))

    assert [segment.translation_vi for segment in translated] == [
        "vui hay buồn",
        "đã tan vỡ rồi",
    ]


def test_lesson_detail_returns_every_subtitle_in_sequence_order():
    lesson = SimpleNamespace(
        id=1,
        title="Sample lesson",
        slug="sample-lesson",
        description=None,
        video_provider="youtube",
        video_id="video-123",
        video_url="https://www.youtube.com/watch?v=video-123",
        thumbnail_url=None,
        duration_seconds=30,
        difficulty="A1",
    )
    subtitles = [
        SimpleNamespace(
            id=2,
            sequence=2,
            start_ms=5000,
            end_ms=9000,
            content_en="Second sentence.",
            translation_vi="Câu thứ hai.",
        ),
        SimpleNamespace(
            id=1,
            sequence=1,
            start_ms=0,
            end_ms=4000,
            content_en="First sentence.",
            translation_vi="Câu đầu tiên.",
        ),
    ]

    response = _build_lesson_detail_response(lesson, subtitles)

    assert response.subtitle_count == 2
    assert [subtitle.id for subtitle in response.subtitles] == [1, 2]
    assert response.subtitles[0].start_ms == 0


def test_save_imported_lesson_flushes_inside_transaction():
    lesson = SimpleNamespace(id=1)
    session = SimpleNamespace(add=Mock(), flush=AsyncMock())

    asyncio.run(_save_imported_lesson.__wrapped__(lesson, session))

    session.add.assert_called_once_with(lesson)
    session.flush.assert_awaited_once()


def test_save_imported_lesson_returns_conflict_for_integrity_error():
    error = IntegrityError("INSERT", {}, Exception("duplicate"))
    session = SimpleNamespace(
        add=Mock(),
        flush=AsyncMock(side_effect=error),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            _save_imported_lesson.__wrapped__(SimpleNamespace(id=1), session)
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "The lesson conflicts with an existing record"


def test_delete_lesson_requires_admin():
    request = SimpleNamespace(state=SimpleNamespace(role="user"))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(delete_lesson("sample-lesson", request, SimpleNamespace()))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin role required"


def test_delete_lesson_uses_shared_delete_helper(monkeypatch):
    delete_record = AsyncMock()
    monkeypatch.setattr(
        "app.features.lesson.service.async_delete_one_record_by",
        delete_record,
    )
    session = SimpleNamespace()

    asyncio.run(LessonService.delete_lesson("sample-lesson", session))

    delete_record.assert_awaited_once()
    args, kwargs = delete_record.await_args
    assert args[0].__name__ == "Lesson"
    assert args[1] is session
    assert kwargs["search_criteria"]
