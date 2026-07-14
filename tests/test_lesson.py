from types import SimpleNamespace

import pytest

from app.features.lesson.service import (
    _build_lesson_player_response,
    _extract_youtube_video_id,
    _group_transcript,
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


def test_group_transcript_preserves_spoken_content_and_timing():
    raw_snippets = [
        {"text": "What is the", "start": 0.0, "duration": 1.2},
        {"text": "difference?", "start": 1.2, "duration": 0.8},
        {"text": "[Music]", "start": 2.0, "duration": 1.0},
        {"text": "This is the answer.", "start": 3.0, "duration": 2.0},
    ]

    segments = _group_transcript(raw_snippets)

    assert [segment["content_en"] for segment in segments] == [
        "What is the difference?",
        "This is the answer.",
    ]
    assert segments[0]["start_seconds"] == 0.0
    assert segments[0]["end_seconds"] == 2.0
    assert segments[1]["start_seconds"] == 3.0


def test_lesson_player_returns_every_subtitle_in_sequence_order():
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

    response = _build_lesson_player_response(lesson, subtitles)

    assert response.subtitle_count == 2
    assert [subtitle.id for subtitle in response.subtitles] == [1, 2]
    assert response.subtitles[0].start_ms == 0
