import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.features.dictionary.service import DictionaryService
from app.features.dictionary.schemas import PhoneticItem
from app.features.vocabulary.model import VocabularyProgress
from app.features.vocabulary.service import (
    VocabularyService,
    _build_topic_word_response,
)
from app.features.wordlist.schemas import (
    SavedWordFilter,
    SavedWordsDueFilter,
    SavedWordsDueResponse,
    SaveWordRequest,
)
from app.features.wordlist.service import (
    WordListService,
    _build_saved_word_response,
    _build_saved_word_review_response,
    _calculate_srs_schedule,
    _get_or_create_vocabularies,
)
from app.main import app
from app.utils.constants import ReviewRating, WordStatus


def test_save_request_strips_word_and_rejects_blank_word():
    assert SaveWordRequest(word="  take off  ").word == "take off"

    with pytest.raises(ValidationError):
        SaveWordRequest(word="   ")


def test_list_filter_ignores_blank_keyword():
    filters = SavedWordFilter(keyword="   ")

    assert filters.keyword is None
    assert filters.page == 1
    assert filters.page_size == 10


def test_saved_word_list_filter_does_not_expose_progress_status():
    assert "status" not in SavedWordFilter.model_json_schema()["properties"]


def test_word_list_and_vocabulary_routes_are_separated():
    paths = app.openapi()["paths"]

    assert "/api/v1/word-lists/{word_list_id}/words" in paths
    assert "/api/v1/word-lists/{word_list_id}/review/due" in paths
    assert "/api/v1/vocabulary/books" in paths
    assert "/api/v1/vocabulary/due" not in paths


def test_get_book_topics_includes_new_word_count(monkeypatch):
    topic = SimpleNamespace(
        id=2,
        book_id=1,
        name="Contract",
        slug="contract",
        order_num=1,
    )

    class FakeSession:
        async def exec(self, statement):
            return SimpleNamespace(all=lambda: [(topic, 15, 1, 14, 0)])

    monkeypatch.setattr(
        "app.features.vocabulary.service.async_get_one_record_by",
        AsyncMock(return_value=SimpleNamespace(id=1)),
    )

    result = asyncio.run(
        VocabularyService.get_book_topics(7, "toeic-600", FakeSession())
    )

    assert len(result) == 1
    assert result[0].word_count == 15
    assert result[0].mastered_word_count == 1
    assert result[0].learning_word_count == 14
    assert result[0].new_word_count == 0


def test_saved_word_list_queries_notebook_items(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.statements = []

        async def exec(self, statement):
            self.statements.append(str(statement))
            if len(self.statements) == 1:
                return SimpleNamespace(one=lambda: 0)
            return SimpleNamespace(all=lambda: [])

    monkeypatch.setattr(
        "app.features.wordlist.service._get_user_word_list",
        AsyncMock(return_value=SimpleNamespace(id=3)),
    )
    session = FakeSession()

    items, total, pages = asyncio.run(
        WordListService.get_saved_words(
            user_id=1,
            word_list_id=3,
            filters=SavedWordFilter(),
            session=session,
        )
    )

    assert items == []
    assert total == 0
    assert pages == 0
    assert len(session.statements) == 2
    assert all('"NotebookItem"' in statement for statement in session.statements)
    assert all("vocabulary_progress" not in statement for statement in session.statements)


def test_saved_words_due_uses_page_and_page_size(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.statements = []

        async def exec(self, statement):
            self.statements.append(statement)
            if len(self.statements) == 1:
                return SimpleNamespace(one=lambda: 21)
            return SimpleNamespace(all=lambda: [])

    monkeypatch.setattr(
        "app.features.wordlist.service._get_user_word_list",
        AsyncMock(return_value=SimpleNamespace(id=3)),
    )
    session = FakeSession()

    items, total, pages = asyncio.run(
        WordListService.get_saved_words_due(
            user_id=1,
            word_list_id=3,
            filters=SavedWordsDueFilter(page=2, page_size=10),
            session=session,
        )
    )

    assert items == []
    assert total == 21
    assert pages == 3
    assert session.statements[1]._offset_clause.value == 10
    assert session.statements[1]._limit_clause.value == 10


def test_saved_words_due_response_uses_pagination_metadata():
    properties = SavedWordsDueResponse.model_json_schema()["properties"]

    assert "metadata" in properties
    assert "total_due" not in properties


def test_new_vocabulary_progress_starts_with_new_status():
    assert WordStatus.NEW.value == "new"
    assert VocabularyProgress.__table__.c.status.default.arg == "new"


def test_srs_again_and_hard_repeat_within_the_learning_stage():
    reviewed_at = datetime(2026, 7, 16, 9, tzinfo=timezone.utc)
    progress = SimpleNamespace(
        repetition_count=3,
        interval_days=8,
        ease_factor=2.50,
    )

    again = _calculate_srs_schedule(progress, ReviewRating.AGAIN, reviewed_at)
    assert again["repetition_count"] == 0
    assert again["interval_days"] == 0
    assert again["ease_factor"] == 2.30
    assert again["next_review_at"] == reviewed_at.replace(minute=10)
    assert again["status"] == WordStatus.LEARNING.value

    new_progress = SimpleNamespace(
        repetition_count=0,
        interval_days=0,
        ease_factor=2.50,
    )
    hard = _calculate_srs_schedule(new_progress, ReviewRating.HARD, reviewed_at)
    assert hard["repetition_count"] == 0
    assert hard["interval_days"] == 0
    assert hard["ease_factor"] == 2.35
    assert hard["next_review_at"] == reviewed_at.replace(hour=21)
    assert hard["status"] == WordStatus.LEARNING.value


def test_srs_good_uses_configured_interval_progression():
    reviewed_at = datetime(2026, 7, 16, 9, tzinfo=timezone.utc)
    expected_intervals = [1, 3, 5, 8, 15, 21]

    for repetition_count, expected_interval in enumerate(expected_intervals):
        progress = SimpleNamespace(
            repetition_count=repetition_count,
            interval_days=(
                0
                if repetition_count == 0
                else expected_intervals[repetition_count - 1]
            ),
            ease_factor=2.50,
        )
        schedule = _calculate_srs_schedule(
            progress, ReviewRating.GOOD, reviewed_at
        )
        assert schedule["interval_days"] == expected_interval

    assert schedule["status"] == WordStatus.MASTERED.value


def test_srs_easy_increases_interval_and_ease_factor():
    reviewed_at = datetime(2026, 7, 16, 9, tzinfo=timezone.utc)
    progress = SimpleNamespace(
        repetition_count=1,
        interval_days=1,
        ease_factor=2.50,
    )

    schedule = _calculate_srs_schedule(progress, ReviewRating.EASY, reviewed_at)

    assert schedule["repetition_count"] == 2
    assert schedule["interval_days"] == 4
    assert schedule["ease_factor"] == 2.65
    assert schedule["status"] == WordStatus.REVIEW.value


def test_save_uses_stored_entries_or_creates_ai_meanings(monkeypatch):
    records = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    lookup = AsyncMock(return_value=records)
    bulk_create = AsyncMock(
        side_effect=lambda _, data, __: [
            SimpleNamespace(**item) for item in data
        ]
    )
    monkeypatch.setattr(
        "app.features.wordlist.service.async_get_many_records_by",
        lookup,
    )
    monkeypatch.setattr(
        "app.features.wordlist.service.async_create_bulk_records",
        bulk_create,
    )

    result = asyncio.run(
        _get_or_create_vocabularies(
            SaveWordRequest(word="record"),
            object(),
        )
    )
    assert result == records
    bulk_create.assert_not_awaited()

    lookup.return_value = []
    result = asyncio.run(
        _get_or_create_vocabularies(
            SaveWordRequest(
                word="record",
                meanings=[
                    {
                        "part_of_speech": "noun",
                        "ipa": "/ˈrek.ɔːd/",
                        "audio_url": "https://audio.test/record-noun.mp3",
                        "definitions": [{"definition_vi": "bản ghi"}],
                    },
                    {
                        "part_of_speech": "verb",
                        "ipa": "/rɪˈkɔːd/",
                        "definitions": [{"definition_vi": "ghi lại"}],
                    },
                ],
            ),
            object(),
        )
    )
    assert [record.word_type for record in result] == ["noun", "verb"]
    assert [record.ipa for record in result] == ["/ˈrek.ɔːd/", "/rɪˈkɔːd/"]
    assert result[0].audio_url == "https://audio.test/record-noun.mp3"

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            _get_or_create_vocabularies(
                SaveWordRequest(word="unknown"),
                object(),
            )
        )
    assert error.value.status_code == 422


def test_dictionary_response_uses_requested_word_and_validates_meanings():
    response = DictionaryService._build_response(
        "take off",
        {
            "word": "incorrect word",
            "meanings": [
                {
                    "part_of_speech": "phrasal verb",
                    "ipa": "/teɪk ɒf/",
                    "audio_url": "https://audio.test/take-off.mp3",
                    "definitions": [{"definition_vi": "cởi ra"}],
                }
            ],
        },
        [],
        ["ai-dictionary"],
    )

    assert response.word == "take off"
    assert response.meanings[0].ipa == "/teɪk ɒf/"
    assert response.meanings[0].audio_url == "https://audio.test/take-off.mp3"
    assert response.meanings[0].definitions[0].definition_vi == "cởi ra"

    with pytest.raises(HTTPException) as error:
        DictionaryService._build_response(
            "take off",
            {"meanings": [{"part_of_speech": "verb", "definitions": []}]},
            [],
            ["ai-dictionary"],
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Word or phrase not found"


def test_dictionary_attaches_real_audio_to_single_meaning():
    response = DictionaryService._build_response(
        "heyday",
        {
            "meanings": [
                {
                    "part_of_speech": "noun",
                    "ipa": "/ˈheɪ.deɪ/",
                    "definitions": [
                        {"definition_vi": "thời hoàng kim, thời huy hoàng"}
                    ],
                }
            ]
        },
        [
            PhoneticItem(
                ipa="/ˈheɪdeɪ/",
                audio="https://audio.test/heyday-us.mp3",
            )
        ],
        ["ai-dictionary"],
    )

    assert response.meanings[0].ipa == "/ˈheɪ.deɪ/"
    assert response.meanings[0].audio_url == "https://audio.test/heyday-us.mp3"
    assert "phonetics" not in response.model_dump()


def test_dictionary_prompt_escapes_word_for_json_template():
    prompt = DictionaryService._build_prompt('say "hello"')

    assert '"word": "say \\"hello\\""' in prompt
    assert "Never invent a definition or suggest a replacement word" in prompt


def test_saved_word_response_uses_notebook_item_data():
    vocabulary_created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    saved_at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    vocab = SimpleNamespace(
        id=1,
        word="take off",
        word_type="verb",
        ipa=None,
        audio_url=None,
        image_url=None,
        definition_vi="cởi ra",
        example_sentence=None,
        example_translation_vi=None,
        created_time=vocabulary_created_at,
    )
    progress = SimpleNamespace(
        status="learning",
        ease_factor=2.5,
        repetition_count=0,
        interval_days=0,
        next_review_at=None,
        last_reviewed_at=None,
        personal_note="remember this",
        created_time=saved_at,
    )
    item = SimpleNamespace(
        id=9,
        notebook_id=3,
        source_subtitle_id=7,
        context_sentence="Take off your coat.",
        note="from lesson 1",
        created_time=saved_at,
    )

    response = _build_saved_word_response(vocab, item)
    review_response = _build_saved_word_review_response(vocab, progress, item)

    assert response.created_time == saved_at
    assert response.word_list_item_id == 9
    assert response.word_list_id == 3
    assert response.source_subtitle_id == 7
    assert response.context_sentence == "Take off your coat."
    assert response.note == "from lesson 1"
    assert "status" not in response.model_dump()
    assert review_response.status == "learning"
    assert review_response.ease_factor == 2.5
    assert review_response.personal_note == "remember this"


def test_topic_word_response_uses_defaults_only_when_progress_is_missing():
    vocab = SimpleNamespace(
        id=1,
        word="take off",
        word_type="verb",
        ipa=None,
        audio_url=None,
        image_url=None,
        definition_vi="cởi ra",
        example_sentence=None,
        example_translation_vi=None,
    )

    response = _build_topic_word_response(vocab, order_num=1)

    assert response.status is None
    assert response.repetition_count == 0
