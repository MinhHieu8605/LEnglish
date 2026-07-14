from typing import List, Optional

from pydantic import BaseModel, Field


class DefinitionItem(BaseModel):
    """
    A single definition with an optional example.

    Attributes:
        definition (str): The definition text.
        example (Optional[str]): An example usage of the word.
    """
    definition_vi: str
    example: Optional[str] = None
    example_vi: Optional[str] = None


class MeaningItem(BaseModel):
    """
    A group of definitions for a specific part of speech.

    Attributes:
        part_of_speech (str): The grammatical category (noun, verb, etc.).
        definitions (List[DefinitionItem]): One or more definitions.
    """
    part_of_speech: str
    ipa: Optional[str] = None
    audio_url: Optional[str] = None
    definitions: List[DefinitionItem]


class PhoneticItem(BaseModel):
    """
    Phonetic transcription and audio URL.

    Attributes:
        ipa (Optional[str]): Phonetic transcription (IPA).
        audio (Optional[str]): URL to pronunciation audio.
    """
    ipa: Optional[str] = None
    audio: Optional[str] = None


class DictionaryLookupResponse(BaseModel):
    """
    Response model for dictionary lookups.

    Attributes:
        word (str): The looked-up word.
        meanings (List[MeaningItem]): Definitions grouped by part of speech.
        sources (List[str]): Data sources used to build the entry.
    """
    word: str
    meanings: List[MeaningItem] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
