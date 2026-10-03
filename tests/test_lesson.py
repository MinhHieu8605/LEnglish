import asyncio
from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from app.api.v1.endpoint.lesson import delete_lesson
from app.features.lesson.service import _slugify
from app.features.lesson.youtube import _extract_youtube_video_id, _group_transcript


@pytest.mark.parametrize(
    ("video_url", "expected"),
    [
        ("https://www.youtube.com/watch?v=iISY9FgeYpU", "iISY9FgeYpU"),
        ("https://youtu.be/iISY9FgeYpU", "iISY9FgeYpU"),
    ],
)
def test_extract_youtube_video_id(video_url, expected):
    assert _extract_youtube_video_id(video_url) == expected


@pytest.mark.parametrize("video_url", ["not-a-url", "https://youtube.com/"])
def test_extract_youtube_video_id_rejects_incomplete_urls(video_url):
    with pytest.raises(ValueError):
        _extract_youtube_video_id(video_url)


def test_group_transcript_deduplicates_nearly_adjacent_rolling_captions():
    segments = _group_transcript(
        [
            {"text": "We need to practice", "start": 0.0, "duration": 2.0},
            {"text": "practice every day.", "start": 2.05, "duration": 2.0},
        ]
    )

    assert [segment.content_en for segment in segments] == [
        "We need to practice every day."
    ]


def test_group_transcript_does_not_add_spaces_before_punctuation():
    segments = _group_transcript(
        [
            {"text": "Hello", "start": 0.0, "duration": 1.0},
            {"text": ", world!", "start": 1.0, "duration": 1.0},
        ]
    )

    assert [segment.content_en for segment in segments] == ["Hello, world!"]


def test_group_transcript_splits_long_cue_only_at_whole_words():
    text = " ".join(f"word{index}" for index in range(1, 31))

    segments = _group_transcript(
        [{"text": text, "start": 0.0, "duration": 20.0}]
    )

    assert len(segments) >= 2
    assert " ".join(segment.content_en for segment in segments) == text
    assert all(len(segment.content_en.split()) <= 18 for segment in segments)
    assert all(
        segment.end_seconds - segment.start_seconds <= 10.0
        for segment in segments
    )


def test_group_transcript_keeps_a_short_sentence_intact():
    text = (
        "At 70, we say, I would give up everything for my mom to be here "
        "with me."
    )

    segments = _group_transcript(
        [{"text": text, "start": 0.0, "duration": 8.06}]
    )

    assert [segment.content_en for segment in segments] == [text]


def test_lesson_slug_is_url_safe():
    assert _slugify("  Tiếng Anh Giao Tiếp!  ") == "tieng-anh-giao-tiep"


def test_delete_lesson_requires_admin():
    request = SimpleNamespace(state=SimpleNamespace(role="user"))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(delete_lesson("lesson", request, SimpleNamespace()))

    assert exc_info.value.status_code == 403
