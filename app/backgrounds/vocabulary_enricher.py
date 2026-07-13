"""Background worker for AI enrichment of vocabulary entries."""

import asyncio
import json

from loguru import logger

from app.database.async_db import (
    async_get_one_record_by_id,
    async_update_one_record,
    get_session,
)
from app.features.vocabulary.model import Vocabulary
from app.utils.ai_client import call_ai
from app.utils.constants import WordType

_AI_VOCAB_SYSTEM_PROMPT = (
    "You are an English vocabulary analyzer. Given a word or phrase, "
    "determine its part of speech and provide the most common Vietnamese definition.\n\n"
    "Respond ONLY with valid JSON (no markdown, no code fences):\n"
    '{\n'
    '  "ipa": "IPA transcription (e.g. /həˈloʊ/)",\n'
    '  "word_type": "noun|verb|adjective|adverb|preposition|conjunction|pronoun|interjection|determiner|exclamation",\n'
    '  "definition_vi": "Vietnamese translation",\n'
    '  "example_sentence": "English example sentence",\n'
    '  "example_translation_vi": "Vietnamese translation of the example"\n'
    '}\n\n'
    "Rules:\n"
    "- word_type must be one of the 10 types listed above\n"
    "- For phrases, use the most appropriate type\n"
    "- definition_vi: concise, most common meaning\n"
    "- ipa: full IPA for the entire word/phrase including spaces between words"
)


# ---------------------------------------------------------------------------
# Singleton — import this from endpoints and main.py
# ---------------------------------------------------------------------------
_enricher: "VocabularyEnricher | None" = None
_MAX_ENRICH_RETRIES = 3
_VALID_WORD_TYPES = {word_type.value for word_type in WordType}


def get_enricher() -> "VocabularyEnricher":
    global _enricher
    if _enricher is None:
        _enricher = VocabularyEnricher()
    return _enricher


class VocabularyEnricher(object):
    """Background worker that enriches vocabulary via AI after creation.

    Usage:
        enricher = VocabularyEnricher()
        enricher.start()           # startup
        enricher.enqueue(vocab_id) # after saving a new word
        enricher.stop()            # shutdown
    """

    def __init__(self):
        self._queue: asyncio.Queue[tuple[int, int]] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    # ---- lifecycle ----

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="vocab-enricher")
        logger.info("VocabularyEnricher started")


    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("VocabularyEnricher stopped")

    # ---- public API ----

    def enqueue(self, vocab_id: int) -> None:
        """Schedule a vocabulary for AI enrichment."""
        self._queue.put_nowait((vocab_id, 0))

    # ---- internals ----

    async def _run(self) -> None:
        while True:
            vocab_id, attempt = await self._queue.get()
            try:
                await self._enrich_one(vocab_id)
            except Exception:
                if attempt < _MAX_ENRICH_RETRIES:
                    logger.warning(
                        f"Vocabulary enrichment failed for vocab_id={vocab_id}; retrying "
                        f"({attempt + 1}/{_MAX_ENRICH_RETRIES})"
                    )
                    self._queue.put_nowait((vocab_id, attempt + 1))
                else:
                    logger.exception(
                        f"Vocabulary enrichment failed permanently for vocab_id={vocab_id}"
                    )
            finally:
                self._queue.task_done()


    async def _enrich_one(self, vocab_id: int) -> None:
        """Fetch vocab by id, call AI, update DB — with own session."""
        async for session in get_session():
            vocab = await async_get_one_record_by_id(
                Vocabulary, vocab_id, session, raise_if_not_found=False,
            )
            if vocab is None:
                return

            content = await call_ai(
                    prompt=f"Analyze this English word or phrase: '{vocab.word}'",
                    system_prompt=_AI_VOCAB_SYSTEM_PROMPT,
                    temperature=0.1,
                    max_tokens=500,
                    service_name="vocabulary",
                )
            data = json.loads(content)
            required_fields = (
                "ipa", "word_type", "definition_vi", "example_sentence", "example_translation_vi"
            )
            if not all(isinstance(data.get(field), str) and data[field].strip() for field in required_fields):
                raise ValueError("AI vocabulary response is missing required fields")
            if data["word_type"] not in _VALID_WORD_TYPES:
                raise ValueError(f"Unsupported word type: {data['word_type']}")

            await async_update_one_record(
                Vocabulary,
                vocab.id,
                {field: data[field].strip() for field in required_fields},
                session,
            )
