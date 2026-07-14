import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.features.dictionary.service import DictionaryService
from app.features.dictionary.schemas import PhoneticItem
from app.features.vocabulary.schemas import VocabularyListFilter, VocabularySaveRequest
from app.features.vocabulary.model import VocabularyProgress
from app.features.vocabulary.service import (
    _build_notebook_vocabulary_response,
    _build_topic_word_response,
    _build_vocabulary_response,
    _get_or_create_vocabularies,
)
from app.utils.constants import WordStatus


def test_save_request_strips_word_and_rejects_blank_word():
    assert VocabularySaveRequest(word="  take off  ").word == "take off"

    with pytest.raises(ValidationError):
        VocabularySaveRequest(word="   ")


def test_list_filter_ignores_blank_keyword():
    assert VocabularyListFilter(keyword="   ").keyword is None


def test_new_vocabulary_progress_starts_with_new_status():
    assert WordStatus.NEW.value == "new"
    assert VocabularyProgress.__table__.c.status.default.arg == "new"


def test_save_uses_stored_entries_or_creates_ai_meanings(monkeypatch):
    records = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    lookup = AsyncMock(return_value=records)
    bulk_create = AsyncMock(
        side_effect=lambda _, data, __: [
            SimpleNamespace(**item) for item in data
        ]
    )
    monkeypatch.setattr(
        "app.features.vocabulary.service.async_get_many_records_by",
        lookup,
    )
    monkeypatch.setattr(
        "app.features.vocabulary.service.async_create_bulk_records",
        bulk_create,
    )

    result = asyncio.run(
        _get_or_create_vocabularies(
            VocabularySaveRequest(word="record"),
            object(),
        )
    )
    assert result == records
    bulk_create.assert_not_awaited()

    lookup.return_value = []
    result = asyncio.run(
        _get_or_create_vocabularies(
            VocabularySaveRequest(
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
                VocabularySaveRequest(word="unknown"),
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


def test_vocabulary_response_uses_user_saved_time_not_global_word_time():
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
    )

    response = _build_vocabulary_response(vocab, progress)
    notebook_response = _build_notebook_vocabulary_response(vocab, progress, item)

    assert response.created_time == saved_at
    assert "context_sentence" not in response.model_dump()
    assert notebook_response.notebook_item_id == 9
    assert notebook_response.source_subtitle_id == 7
    assert notebook_response.context_sentence == "Take off your coat."
    assert notebook_response.note == "from lesson 1"


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
