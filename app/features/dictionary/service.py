import asyncio
import json
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status
from loguru import logger
from pydantic import ValidationError
from sqlmodel import func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import async_get_many_records_by
from app.features.dictionary.schemas import (
    DictionaryLookupResponse,
    DefinitionItem,
    MeaningItem,
    PhoneticItem,
)
from app.features.vocabulary.model import Vocabulary
from app.utils.ai_client import call_ai


FREE_DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"
_SOURCE_DB = "local-database"
_SOURCE_AI = "ai-dictionary"

_AI_DICTIONARY_SYSTEM_PROMPT = (
    "You are a professional English-Vietnamese dictionary. "
    "You provide complete, accurate dictionary entries for any English word "
    "or phrase, including phrasal verbs, idioms, and slang.\n\n"
    "Rules:\n"
    "1. definition_vi: Core, most common Vietnamese equivalent(s). "
    "Prioritize high-frequency, natural words that Vietnamese speakers naturally use in daily life "
    "(e.g., 'abide by' → 'tuân theo', 'obligate' → 'bắt buộc, ép buộc'). Avoid overly formal, rigid, or heavy Sino-Vietnamese (Hán-Việt) "
    "words unless the English word itself is highly formal or technical. Max 2 alternatives separated by a comma.\n"
    "2. example: A natural English sentence using the word in this specific context.\n"
    "3. example_vi: Accurate Vietnamese translation of the example sentence.\n"
    "4. Every definition block MUST have all 4 fields filled (never null).\n"
    "5. Always respond with valid JSON only. Do not wrap inside markdown blocks."
)

class DictionaryService(object):
    """
    Service for looking up word definitions.

    Uses AI as the primary dictionary source (supports all words including
    phrasal verbs, idioms, etc.) and Free Dictionary API as a secondary
    source for phonetics/audio.
    """

    @classmethod
    async def _fetch_phonetics(cls, word: str) -> list[PhoneticItem]:
        """
        Fetch phonetics (IPA + audio) from Free Dictionary API.

        This is best-effort — if the API doesn't have the word (e.g. phrasal
        verbs), we return an empty list instead of failing.

        Args:
            word (str): The word to look up phonetics for.

        Returns:
            list[PhoneticItem]: Phonetic transcriptions and audio URLs.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{FREE_DICT_URL}/{quote(word, safe='')}")

            if response.status_code != status.HTTP_200_OK:
                return []

            data = response.json()[0]
            phonetics = []
            for item in data.get("phonetics") or []:
                text = item.get("text")
                audio = item.get("audio")
                if text or audio:
                    phonetics.append(PhoneticItem(text=text, audio=audio))
            return phonetics

        except Exception as e:
            logger.debug(f"Free Dictionary phonetics unavailable for '{word}': {e}")
            return []

    @classmethod
    def _build_prompt(cls, word: str) -> str:
        """Build user prompt for AI dictionary lookup."""
        return (
            f"Provide a complete dictionary entry for: '{word}'\n\n"
            f"Return a JSON object matching this exact structure:\n"
            f'{{\n'
            f'  "word": {json.dumps(word, ensure_ascii=False)},\n'
            f'  "phonetics": [\n'
            f'    {{\n'
            f'      "text": "IPA transcription (e.g. /həˈloʊ/)",\n'
            f'      "audio": ""\n'
            f'    }}\n'
            f'  ],\n'
            f'  "meanings": [\n'
            f'    {{\n'
            f'      "part_of_speech": "noun/verb/adjective/etc.",\n'
            f'      "definitions": [\n'
            f'        {{\n'
            f'          "definition_vi": "Vietnamese translation",\n'
            f'          "example": "English example sentence",\n'
            f'          "example_vi": "Vietnamese example translation"\n'
            f'        }}\n'
            f'      ]\n'
            f'    }}\n'
            f'  ]\n'
            f'}}\n\n'
            f"Include all common parts of speech. For each part of speech, include "
            f"its most common distinct meanings/senses. Return ONLY valid JSON."
        )

    @classmethod
    async def _call_ai_api(cls, prompt: str) -> str:
        """Call external AI API and return raw response content.

        Raises:
            HTTPException 503: If API is unavailable.
            HTTPException 502: If API returns error status.
        """
        return await call_ai(
            prompt=prompt,
            system_prompt=_AI_DICTIONARY_SYSTEM_PROMPT,
            service_name="dictionary",
        )

    @classmethod
    def _parse_ai_response(cls, content: str) -> dict:
        """Parse AI response, stripping markdown fences if present."""
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)

    @classmethod
    async def _ai_lookup(cls, word: str) -> dict:
        """Use AI to generate a complete dictionary entry.

        Returns:
            dict: Parsed AI response with meanings.

        Raises:
            HTTPException: If AI API is unavailable or returns invalid data.
        """
        prompt = cls._build_prompt(word)
        content = await cls._call_ai_api(prompt)
        try:
            parsed = cls._parse_ai_response(content)
            if not isinstance(parsed, dict):
                raise ValueError("AI response is not a JSON object")
            return parsed
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI dictionary returned invalid data",
            )

    @classmethod
    async def _db_lookup(cls, word: str, session: AsyncSession) -> dict | None:
        """Look up word in local vocabulary database.

        Returns parsed AI-style dict if found with definition data, else None.
        """
        records = await async_get_many_records_by(
            Vocabulary,
            [func.lower(Vocabulary.word) == word.lower()],
            session,
            raise_if_not_found=False,
        )
        if not records:
            return None

        meanings = []
        for item in records:
            if not item.definition_vi or not item.word_type:
                continue
            meanings.append({
                "part_of_speech": item.word_type,
                "definitions": [{
                    "definition_vi": item.definition_vi,
                    "example": item.example_sentence,
                    "example_vi": item.example_translation_vi,
                }],
            })

        if not meanings:
            return None

        return {
            "word": records[0].word,
            "meanings": meanings,
        }

    @classmethod
    def _build_response(
        cls, word: str, data: dict, free_phonetics: list, sources: list[str]
    ) -> DictionaryLookupResponse:
        """Build response from dictionary data + phonetics.

        Dedup phonetics: if multiple entries share the same text,
        keep only the one with audio.
        """
        try:
            phonetics = free_phonetics or []
            if not phonetics and data.get("phonetics"):
                phonetics = [
                    PhoneticItem.model_validate({"text": item.get("text")})
                    for item in data["phonetics"]
                    if isinstance(item, dict) and item.get("text")
                ]
            else:
                seen = {}
                for phonetic in phonetics:
                    key = phonetic.text or ""
                    if key not in seen or (phonetic.audio and not seen[key].audio):
                        seen[key] = phonetic
                phonetics = list(seen.values())

            meanings = [
                MeaningItem.model_validate(
                    {
                        "part_of_speech": meaning.get("part_of_speech", "unknown"),
                        "definitions": [DefinitionItem.model_validate(definition) for definition in meaning.get("definitions") or []],
                    }
                )
                for meaning in data.get("meanings") or []
                if isinstance(meaning, dict)
            ]
        except (TypeError, ValidationError, ValueError) as error:
            logger.error(f"Invalid dictionary response: {error}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Dictionary returned invalid data",
            )

        if not any(meaning.definitions for meaning in meanings):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Dictionary returned no definitions",
            )

        return DictionaryLookupResponse(
            word=word,
            phonetics=phonetics,
            meanings=meanings,
            sources=sources,
        )

    @classmethod
    async def lookup(cls, word: str, session: AsyncSession | None = None) -> DictionaryLookupResponse:
        """
        Look up a word using AI as the primary dictionary source,
        with Free Dictionary API providing phonetics/audio.

        Supports regular words, phrasal verbs (e.g. 'abide by'),
        idioms, and slang.

        Args:
            word (str): The word or phrase to look up.

        Returns:
            DictionaryLookupResponse: Complete dictionary data including
                phonetics, definitions (EN + VI), examples (EN + VI).

        Raises:
            HTTPException 503: If AI service is unavailable.
            HTTPException 502: If AI returns invalid data.
        """
        word = word.strip().lower()
        if not word:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Word must not be blank",
            )

        # Check DB first — skip AI if we have cached data
        db_data = await cls._db_lookup(word, session) if session else None

        if db_data:
            phonetics = await cls._fetch_phonetics(word)
            return cls._build_response(word, db_data, phonetics, [_SOURCE_DB])

        ai_data, free_phonetics = await asyncio.gather(
            cls._ai_lookup(word),
            cls._fetch_phonetics(word),
        )

        return cls._build_response(word, ai_data, free_phonetics, [_SOURCE_AI])
