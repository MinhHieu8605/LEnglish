import asyncio
import json
import re
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status
from loguru import logger
from pydantic import ValidationError
from sqlmodel import func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import async_get_many_records_by
from app.features.dictionary.schemas import (
    DefinitionItem,
    DictionaryLookupResponse,
    MeaningItem,
    PhoneticItem,
)
from app.features.vocabulary.model import Vocabulary
from app.utils.ai_client import call_ai

FREE_DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"
_SOURCE_DB = "local-database"
_SOURCE_AI = "ai-dictionary"


def _normalize_ipa(value: str | None) -> str:
    """
    Remove whitespace, periods, and slashes before comparing IPA transcriptions.

    Args:
        value (str | None): The IPA transcription to normalize, or None.

    Returns:
        str: The normalized transcription, or an empty string for None.
    """
    return re.sub(r"[\s./]", "", value or "")


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
    "4. ipa: IPA pronunciation for this specific part of speech.\n"
    "5. audio_url: Use null unless a real pronunciation URL is provided; never invent a URL.\n"
    "6. Every definition block MUST have all fields filled (never null).\n"
    "7. If the input is not a real English word or recognized phrase, return an "
    "empty meanings array and do not invent a definition.\n"
    "8. Always respond with valid JSON only. Do not wrap inside markdown blocks."
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
                ipa = item.get("text")  # text = ipa
                audio = item.get("audio")
                if ipa or audio:
                    phonetics.append(PhoneticItem(ipa=ipa, audio=audio))
            return phonetics

        except Exception as e:
            logger.debug(f"Free Dictionary phonetics unavailable for '{word}': {e}")
            return []

    @classmethod
    def _build_prompt(cls, word: str) -> str:
        """
        Build user prompt for AI dictionary lookup.

        Args:
            word (str): The vocabulary word to look up.

        Returns:
            str: The dictionary lookup prompt specifying the required JSON structure.
        """
        return (
            f"Provide a complete dictionary entry for: '{word}'\n\n"
            f"Return a JSON object matching this exact structure:\n"
            f"{{\n"
            f'  "word": {json.dumps(word, ensure_ascii=False)},\n'
            f'  "meanings": [\n'
            f"    {{\n"
            f'      "part_of_speech": "noun/verb/adjective/etc.",\n'
            f'      "ipa": "IPA for this part of speech",\n'
            f'      "audio_url": null,\n'
            f'      "definitions": [\n'
            f"        {{\n"
            f'          "definition_vi": "Vietnamese translation",\n'
            f'          "example": "English example sentence",\n'
            f'          "example_vi": "Vietnamese example translation"\n'
            f"        }}\n"
            f"      ]\n"
            f"    }}\n"
            f"  ]\n"
            f"}}\n\n"
            f"For an invalid or misspelled input, return an empty meanings array. "
            f"Never invent a definition or suggest a replacement word.\n"
            f"Include all common parts of speech. For each part of speech, include "
            f"its most common distinct meanings/senses. Return ONLY valid JSON."
        )

    @classmethod
    async def _call_ai_api(cls, prompt: str) -> str:
        """
        Call external AI API and return raw response content.

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
        """
        Parse AI response, stripping markdown fences if present.

        Args:
            content (str): The raw AI response to parse.

        Returns:
            dict: The parsed JSON response after removing any Markdown code fence.

        Raises:
            JSONDecodeError: If the extracted response is not valid JSON.
        """
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)

    @classmethod
    async def _ai_lookup(cls, word: str) -> dict:
        """
        Use AI to generate a complete dictionary entry.

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
        """
        Look up word in local vocabulary database.

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
            meanings.append(
                {
                    "part_of_speech": item.word_type,
                    "ipa": item.ipa,
                    "audio_url": item.audio_url,
                    "definitions": [
                        {
                            "definition_vi": item.definition_vi,
                            "example": item.example_sentence,
                            "example_vi": item.example_translation_vi,
                        }
                    ],
                }
            )

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
        """
        Build a response with pronunciation attached to each meaning.

        Args:
            word (str): The looked-up word.
            data (dict): Dictionary data from AI or DB.
            free_phonetics (list): Phonetic data from Free Dictionary API.
            sources (list[str]): Data sources used to build the entry.

        Returns:
            DictionaryLookupResponse: Complete dictionary data including
        """
        try:
            meanings = [
                MeaningItem.model_validate(
                    {
                        "part_of_speech": meaning.get("part_of_speech", "unknown"),
                        "ipa": meaning.get("ipa"),
                        "audio_url": meaning.get("audio_url"),
                        "definitions": [
                            DefinitionItem.model_validate(definition)
                            for definition in meaning.get("definitions") or []
                        ],
                    }
                )
                for meaning in data.get("meanings") or []
                if isinstance(meaning, dict)
            ]

            if len(meanings) == 1:
                phonetic = next((item for item in free_phonetics if item.audio), None)
                if phonetic is None:
                    phonetic = next(iter(free_phonetics), None)
                if phonetic:
                    meanings[0].ipa = meanings[0].ipa or phonetic.ipa
                    meanings[0].audio_url = meanings[0].audio_url or phonetic.audio
            elif meanings:
                phonetics_by_ipa = {
                    _normalize_ipa(item.ipa): item
                    for item in free_phonetics
                    if item.ipa
                }
                for meaning in meanings:
                    phonetic = phonetics_by_ipa.get(_normalize_ipa(meaning.ipa))
                    if phonetic:
                        meaning.audio_url = meaning.audio_url or phonetic.audio
        except (TypeError, ValidationError, ValueError) as error:
            logger.error(f"Invalid dictionary response: {error}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Dictionary returned invalid data",
            )

        if not any(meaning.definitions for meaning in meanings):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Word or phrase not found",
            )

        return DictionaryLookupResponse(
            word=word,
            meanings=meanings,
            sources=sources,
        )

    @classmethod
    async def lookup(
        cls, word: str, session: AsyncSession | None = None
    ) -> DictionaryLookupResponse:
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
