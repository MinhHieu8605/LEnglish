from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.constants import ReviewRating, WordStatus


class VocabularyDefinitionInput(BaseModel):
    """One dictionary definition submitted when saving a new word."""

    definition_vi: str
    example: Optional[str] = None
    example_vi: Optional[str] = None


class VocabularyMeaningInput(BaseModel):
    """One part-of-speech entry submitted when saving a new word."""

    part_of_speech: str
    ipa: Optional[str] = None
    audio_url: Optional[str] = None
    definitions: List[VocabularyDefinitionInput]


class VocabularySaveRequest(BaseModel):
    """
    Request schema for saving a word to a vocabulary notebook.

    Attributes:
        word (str): The word or phrase to save.
        source_subtitle_id (Optional[int]): Subtitle where the word was clicked.
        context_sentence (Optional[str]): The sentence context where the word was encountered.
        note (Optional[str]): A note for this word in the selected notebook.
    """
    word: str = Field(..., min_length=1, max_length=100, description="The word to save")
    meanings: List[VocabularyMeaningInput] = Field(
        default_factory=list,
        description="Dictionary meanings returned by lookup when the word is not in the database",
    )
    source_subtitle_id: Optional[int] = Field(default=None, ge=1)
    context_sentence: Optional[str] = Field(default=None, description="Context sentence where the word was found")
    note: Optional[str] = Field(default=None, description="Note for this notebook entry")

    @field_validator("word", mode="before")
    @classmethod
    def strip_word(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class VocabularyItemResponse(BaseModel):
    """
    Schema representing a vocabulary word with learning progress.

    Attributes:
        id (int): The vocabulary ID.
        word (str): The original word.
        word_type (str): Grammatical category (noun, verb, adjective, etc.).
        ipa (Optional[str]): International Phonetic Alphabet transcription.
        audio_url (Optional[str]): URL to pronunciation audio.
        definition_vi (str): Vietnamese definition.
        example_sentence (Optional[str]): Example sentence using the word.
        example_translation_vi (Optional[str]): Vietnamese translation of the example.
        status (str): Learning status (learning, reviewing, mastered, ignored).
        repetition_count (int): Number of successful reviews.
        interval_days (int): Days until next review.
        next_review_at (Optional[datetime]): Scheduled next review time.
        last_reviewed_at (Optional[datetime]): Last review timestamp.
        personal_note (Optional[str]): User's personal note.
        created_time (Optional[datetime]): When the user saved this word.
    """
    id: int
    word: str
    word_type: Optional[str]
    ipa: Optional[str]
    audio_url: Optional[str]
    definition_vi: Optional[str]
    example_sentence: Optional[str]
    example_translation_vi: Optional[str]
    status: str
    repetition_count: int
    interval_days: int
    next_review_at: Optional[datetime]
    last_reviewed_at: Optional[datetime]
    personal_note: Optional[str]
    created_time: Optional[datetime]


class NotebookVocabularyItemResponse(VocabularyItemResponse):
    """A saved vocabulary item with data specific to one notebook."""
    notebook_item_id: int
    notebook_id: int
    source_subtitle_id: Optional[int]
    context_sentence: Optional[str]
    note: Optional[str]


class VocabularyListFilter(BaseModel):
    """
    Filter and pagination parameters for listing vocabulary.

    Attributes:
        page (int): Page number (1-based). Defaults to 1.
        page_size (int): Number of items per page. Defaults to 20.
        status (Optional[WordStatus]): Filter by learning status.
        keyword (Optional[str]): Search keyword for word (searches via ILIKE).
    """
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    status: Optional[WordStatus] = Field(default=None, description="Filter by learning status")
    keyword: Optional[str] = Field(default=None, max_length=100, description="Search keyword")

    @field_validator("keyword", mode="before")
    @classmethod
    def strip_keyword(cls, value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        return value.strip() or None


class VocabularyListMeta(BaseModel):
    """
    Pagination metadata for vocabulary list responses.

    Attributes:
        total (int): Total number of items matching the filter.
        page (int): Current page number.
        page_size (int): Number of items per page.
        pages (int): Total number of pages.
    """
    total: int
    page: int
    page_size: int
    pages: int


class VocabularyListResponse(BaseModel):
    """
    Paginated vocabulary list response.

    Attributes:
        data (List[VocabularyItemResponse]): List of vocabulary items.
        meta (VocabularyListMeta): Pagination metadata.
    """
    data: List[VocabularyItemResponse]
    meta: VocabularyListMeta


class VocabularyReviewRequest(BaseModel):
    """
    Request schema for reviewing a vocabulary word.

    Attributes:
        rating (ReviewRating): Review result (correct or wrong).
    """
    rating: ReviewRating


class VocabularyReviewDueResponse(BaseModel):
    """
    Response schema for words due for review.

    Attributes:
        data (List[VocabularyItemResponse]): List of due vocabulary items.
        total_due (int): Total number of words due for review.
    """
    data: List[VocabularyItemResponse]
    total_due: int


class VocabularyBookResponse(BaseModel):
    """Response schema for vocabulary books/collections."""
    id: int
    name: str
    slug: str
    description: Optional[str]
    category: str
    image_url: Optional[str]
    created_time: datetime


class VocabularyTopicResponse(BaseModel):
    """Response schema for topics within a book with user progress stats."""
    id: int
    book_id: int
    name: str
    slug: str
    order_num: int
    word_count: int
    mastered_word_count: int
    learning_word_count: int


class TopicWordResponse(BaseModel):
    """Response schema for a word inside a topic, including user progress if any."""
    id: int
    word: str
    word_type: Optional[str]
    ipa: Optional[str]
    audio_url: Optional[str]
    image_url: Optional[str]
    definition_vi: Optional[str]
    example_sentence: Optional[str]
    example_translation_vi: Optional[str]
    order_num: int
    status: Optional[str] = None
    repetition_count: int = 0
    interval_days: int = 0
    next_review_at: Optional[datetime] = None
