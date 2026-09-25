from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
    new_word_count: int


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
