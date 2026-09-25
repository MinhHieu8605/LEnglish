from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.utils.constants import PracticeScope, ReviewRating, VocabularyDeckMode


class ReviewOptionResponse(BaseModel):
    rating: ReviewRating
    interval_seconds: int
    next_review_at: datetime


class PracticeItemResponse(BaseModel):
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


class PracticeDeckResponse(BaseModel):
    topic_slug: str
    mode: VocabularyDeckMode
    scope: PracticeScope
    total_word_count: int
    due_count: int
    new_count: int
    items: List[PracticeItemResponse]


class PracticeCheckRequest(BaseModel):
    attempt_id: str = Field(..., min_length=1, max_length=100)
    mode: VocabularyDeckMode = VocabularyDeckMode.TYPING
    answer: str = Field(..., max_length=500)
    response_ms: Optional[int] = Field(default=None, ge=0)
    used_hint: bool = False
    revealed_answer: bool = False


class PracticeCheckResponse(BaseModel):
    attempt_id: str
    correct: bool
    correct_answer: str
    review_options: Dict[str, ReviewOptionResponse]


class ClozePracticeRequest(BaseModel):
    attempt_id: str = Field(..., min_length=1, max_length=100)


class GeneratedCloze(BaseModel):
    sentence: str = Field(..., min_length=1, max_length=1000)
    translation_vi: str = Field(default="", max_length=1000)
    hint_vi: str = Field(..., min_length=1, max_length=500)


class ClozePracticeResponse(GeneratedCloze):
    attempt_id: str
    vocabulary_id: int


class VocabularyReviewRequest(BaseModel):
    attempt_id: str = Field(..., min_length=1, max_length=100)
    rating: ReviewRating
    mode: Optional[VocabularyDeckMode] = None
    correct: Optional[bool] = None
    used_hint: bool = False
    revealed_answer: bool = False
    submitted_answer: Optional[str] = Field(default=None, max_length=500)
    response_ms: Optional[int] = Field(default=None, ge=0)


class VocabularyReviewResponse(BaseModel):
    vocabulary_id: int
    attempt_id: str
    rating: ReviewRating
    status: str
    repetition_count: int
    interval_days: int
    interval_seconds: int
    next_review_at: datetime


class PracticeSessionStartRequest(BaseModel):
    scope: PracticeScope = PracticeScope.DUE
    initial_mode: VocabularyDeckMode = VocabularyDeckMode.FLASHCARD


class PracticeSessionItemResponse(BaseModel):
    vocabulary_id: int
    order_num: int
    completed_at: Optional[datetime]
    last_attempt_id: Optional[str]


class PracticeSessionResponse(BaseModel):
    id: int
    topic_slug: str
    scope: PracticeScope
    initial_mode: VocabularyDeckMode
    status: str
    current_position: int
    total_items: int
    started_at: datetime
    completed_at: Optional[datetime]
    items: List[PracticeSessionItemResponse]


class PracticeSessionAttemptRequest(BaseModel):
    vocabulary_id: int
    attempt_id: str = Field(..., min_length=1, max_length=100)
    mode: VocabularyDeckMode
    rating: Optional[ReviewRating] = None
    answer: Optional[str] = Field(default=None, max_length=500)
    correct: Optional[bool] = None
    used_hint: bool = False
    revealed_answer: bool = False
    response_ms: Optional[int] = Field(default=None, ge=0)
