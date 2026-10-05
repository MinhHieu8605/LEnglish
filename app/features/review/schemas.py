from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.utils.constants import ReviewMode, ReviewRating, ReviewScope


class ReviewOptionResponse(BaseModel):
    rating: ReviewRating
    interval_seconds: int
    next_review_at: datetime


class ReviewItemResponse(BaseModel):
    vocabulary_id: int
    word: str
    word_type: Optional[str]
    ipa: Optional[str]
    audio_url: Optional[str]
    image_url: Optional[str]
    definition_vi: Optional[str]
    example_sentence: Optional[str]
    example_translation_vi: Optional[str]
    order_num: int
    status: Optional[str]
    review_options: List[ReviewOptionResponse]


class ReviewQueueResponse(BaseModel):
    topic_slug: str
    mode: ReviewMode
    scope: ReviewScope
    total_word_count: int
    due_count: int
    new_count: int
    items: List[ReviewItemResponse]


class ReviewSummaryResponse(BaseModel):
    due_word_count: int
    daily_new_word_target: int
    new_words_learned_today: int
    remaining_new_words: int


class ReviewCheckRequest(BaseModel):
    attempt_id: str = Field(..., min_length=1, max_length=100)
    mode: ReviewMode = ReviewMode.TYPING
    answer: str = Field(..., max_length=500)
    response_ms: Optional[int] = Field(default=None, ge=0)
    used_hint: bool = False
    revealed_answer: bool = False


class ReviewCheckResponse(BaseModel):
    attempt_id: str
    correct: bool
    correct_answer: str
    review_options: Dict[str, ReviewOptionResponse]


class ReviewClozeRequest(BaseModel):
    attempt_id: str = Field(..., min_length=1, max_length=100)


class GeneratedCloze(BaseModel):
    sentence: str = Field(..., min_length=1, max_length=1000)
    translation_vi: str = Field(default="", max_length=1000)
    hint_vi: str = Field(..., min_length=1, max_length=500)


class ReviewClozeResponse(GeneratedCloze):
    attempt_id: str
    vocabulary_id: int


class ReviewWordRequest(BaseModel):
    attempt_id: str = Field(..., min_length=1, max_length=100)
    rating: ReviewRating
    mode: Optional[ReviewMode] = None
    correct: Optional[bool] = None
    used_hint: bool = False
    revealed_answer: bool = False
    submitted_answer: Optional[str] = Field(default=None, max_length=500)
    response_ms: Optional[int] = Field(default=None, ge=0)


class ReviewWordResponse(BaseModel):
    vocabulary_id: int
    attempt_id: str
    rating: ReviewRating
    status: str
    repetition_count: int
    interval_days: int
    interval_seconds: int
    next_review_at: datetime


class ReviewSessionStartRequest(BaseModel):
    scope: ReviewScope = ReviewScope.DUE
    initial_mode: ReviewMode = ReviewMode.FLASHCARD


class ReviewSessionItemResponse(BaseModel):
    vocabulary_id: int
    order_num: int
    completed_at: Optional[datetime]
    last_attempt_id: Optional[str]


class ReviewSessionResponse(BaseModel):
    id: int
    topic_slug: str
    scope: ReviewScope
    initial_mode: ReviewMode
    status: str
    current_position: int
    total_items: int
    started_at: datetime
    completed_at: Optional[datetime]
    items: List[ReviewSessionItemResponse]


class ReviewSessionAttemptRequest(BaseModel):
    vocabulary_id: int
    attempt_id: str = Field(..., min_length=1, max_length=100)
    mode: ReviewMode
    rating: Optional[ReviewRating] = None
    answer: Optional[str] = Field(default=None, max_length=500)
    correct: Optional[bool] = None
    used_hint: bool = False
    revealed_answer: bool = False
    response_ms: Optional[int] = Field(default=None, ge=0)
