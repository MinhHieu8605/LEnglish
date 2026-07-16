from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.constants import ReviewRating


class WordDefinitionInput(BaseModel):
    """One dictionary definition submitted when saving a new word."""

    definition_vi: str
    example: Optional[str] = None
    example_vi: Optional[str] = None


class WordMeaningInput(BaseModel):
    """One part-of-speech entry submitted when saving a new word."""

    part_of_speech: str
    ipa: Optional[str] = None
    audio_url: Optional[str] = None
    definitions: List[WordDefinitionInput]


class SaveWordRequest(BaseModel):
    """Request for saving a dictionary result to a word list."""

    word: str = Field(..., min_length=1, max_length=100)
    meanings: List[WordMeaningInput] = Field(
        default_factory=list,
        description=(
            "Dictionary meanings returned by lookup when the word is not in the database"
        ),
    )
    source_subtitle_id: Optional[int] = Field(default=None, ge=1)
    context_sentence: Optional[str] = None
    note: Optional[str] = None

    @field_validator("word", mode="before")
    @classmethod
    def strip_word(cls, value: str) -> str:
        """
        Remove surrounding whitespace before validating a word.
        """
        return value.strip() if isinstance(value, str) else value


class SavedWordResponse(BaseModel):
    """A word explicitly saved in one user word list."""

    id: int
    word: str
    word_type: Optional[str]
    ipa: Optional[str]
    audio_url: Optional[str]
    definition_vi: Optional[str]
    example_sentence: Optional[str]
    example_translation_vi: Optional[str]
    created_time: Optional[datetime]
    word_list_item_id: int
    word_list_id: int
    source_subtitle_id: Optional[int]
    context_sentence: Optional[str]
    note: Optional[str]


class SavedWordReviewResponse(SavedWordResponse):
    """A saved word together with its spaced-repetition progress."""

    status: str
    ease_factor: float
    repetition_count: int
    interval_days: int
    next_review_at: Optional[datetime]
    last_reviewed_at: Optional[datetime]
    personal_note: Optional[str]


class SavedWordFilter(BaseModel):
    """Pagination and filtering for words saved in one word list."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    keyword: Optional[str] = Field(default=None, max_length=100)

    @field_validator("keyword", mode="before")
    @classmethod
    def strip_keyword(cls, value: Optional[str]) -> Optional[str]:
        """Trim a search keyword and normalize blank text to ``None``.

        Args:
            value (Optional[str]): Raw search keyword supplied by the client.

        Returns:
            Optional[str]: Trimmed keyword or ``None`` when it is blank.
        """
        if not isinstance(value, str):
            return value
        return value.strip() or None


class SavedWordListMeta(BaseModel):
    """Pagination metadata for a saved-word list."""

    total: int
    page: int
    page_size: int
    pages: int


class SavedWordListResponse(BaseModel):
    """Paginated words saved in one word list."""

    data: List[SavedWordResponse]
    metadata: SavedWordListMeta


class ReviewSavedWordRequest(BaseModel):
    """Review result for one saved word."""

    rating: ReviewRating


class SavedWordsDueFilter(BaseModel):
    """Pagination for words that are due for review."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class SavedWordsDueResponse(BaseModel):
    """Paginated words in a word list that are due for review."""

    data: List[SavedWordReviewResponse]
    metadata: SavedWordListMeta
