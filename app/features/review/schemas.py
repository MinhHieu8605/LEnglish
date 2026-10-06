from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.utils.constants import ReviewMode, ReviewRating, ReviewScope


class ReviewOptionResponse(BaseModel):
    """
    Scheduling preview for a possible review rating.

    Attributes:
        rating (ReviewRating): The selected review difficulty rating.
        interval_seconds (int): The delay before the next review in seconds.
        next_review_at (datetime): The timestamp when the next review becomes due.
    """

    rating: ReviewRating
    interval_seconds: int
    next_review_at: datetime


class ReviewItemResponse(BaseModel):
    """
    Vocabulary content and scheduling options for a review queue item.

    Attributes:
        vocabulary_id (int): The identifier of the vocabulary entry.
        word (str): The vocabulary word to review.
        word_type (Optional[str]): The vocabulary word's part of speech, if available.
        ipa (Optional[str]): The word's IPA transcription, if available.
        audio_url (Optional[str]): The pronunciation audio URL, if available.
        image_url (Optional[str]): The vocabulary illustration URL, if available.
        definition_vi (Optional[str]): The word's Vietnamese definition, if available.
        example_sentence (Optional[str]): An example sentence containing the word, if
            available.
        example_translation_vi (Optional[str]): The Vietnamese translation of the
            example sentence, if available.
        order_num (int): The item's ordering position within its topic or session.
        status (Optional[str]): The current lifecycle state.
        review_options (List[ReviewOptionResponse]): The scheduling previews for
            available review ratings.
    """

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
    """
    Response containing a topic's review queue and due and new word counts.

    Attributes:
        topic_slug (str): The URL slug identifying the vocabulary topic.
        mode (ReviewMode): The selected practice mode.
        scope (ReviewScope): Whether to include due words or all words for review.
        total_word_count (int): The total number of words in the topic.
        due_count (int): The number of words currently due for review.
        new_count (int): The number of words without prior review progress.
        items (List[ReviewItemResponse]): The ordered vocabulary items included in the
            response.
    """

    topic_slug: str
    mode: ReviewMode
    scope: ReviewScope
    total_word_count: int
    due_count: int
    new_count: int
    items: List[ReviewItemResponse]


class ReviewSummaryResponse(BaseModel):
    """
    Response containing due words and progress toward the daily new-word target.

    Attributes:
        due_word_count (int): The number of vocabulary entries currently due for review.
        daily_new_word_target (int): The user's daily target for newly learned words.
        new_words_learned_today (int): The number of first-time reviews in the user's
            current local day.
        remaining_new_words (int): The number of new words still needed to meet today's
            target.
    """

    due_word_count: int
    daily_new_word_target: int
    new_words_learned_today: int
    remaining_new_words: int


class ReviewCheckRequest(BaseModel):
    """
    Request to check a vocabulary answer before selecting a review rating.

    Attributes:
        attempt_id (str): The client-provided identifier used to deduplicate a review
            attempt.
        mode (ReviewMode): The selected practice mode.
        answer (str): The submitted answer text to check.
        response_ms (Optional[int]): The time taken to answer in milliseconds, if
            supplied.
        used_hint (bool): Whether the user requested a hint during the attempt.
        revealed_answer (bool): Whether the correct answer was shown before submission.
    """

    attempt_id: str = Field(..., min_length=1, max_length=100)
    mode: ReviewMode = ReviewMode.TYPING
    answer: str = Field(..., max_length=500)
    response_ms: Optional[int] = Field(default=None, ge=0)
    used_hint: bool = False
    revealed_answer: bool = False


class ReviewCheckResponse(BaseModel):
    """
    Answer check result and scheduling options for the review attempt.

    Attributes:
        attempt_id (str): The client-provided identifier used to deduplicate a review
            attempt.
        correct (bool): Whether the submitted answer is correct.
        correct_answer (str): The expected vocabulary answer.
        review_options (Dict[str, ReviewOptionResponse]): The scheduling previews for
            available review ratings.
    """

    attempt_id: str
    correct: bool
    correct_answer: str
    review_options: Dict[str, ReviewOptionResponse]


class ReviewTopicCheckRequest(ReviewCheckRequest):
    """
    Answer check request scoped to a vocabulary book and topic.

    Attributes:
        book_slug (str): The URL slug identifying the vocabulary book.
        topic_slug (str): The URL slug identifying the vocabulary topic.
    """

    book_slug: str = Field(..., min_length=1)
    topic_slug: str = Field(..., min_length=1)


class ReviewClozeRequest(BaseModel):
    """
    Request to generate a cloze exercise for a review attempt.

    Attributes:
        attempt_id (str): The client-provided identifier used to deduplicate a review
            attempt.
    """

    attempt_id: str = Field(..., min_length=1, max_length=100)


class ReviewTopicClozeRequest(ReviewClozeRequest):
    """
    Cloze request scoped to a vocabulary book and topic.

    Attributes:
        book_slug (str): The URL slug identifying the vocabulary book.
        topic_slug (str): The URL slug identifying the vocabulary topic.
    """

    book_slug: str = Field(..., min_length=1)
    topic_slug: str = Field(..., min_length=1)


class GeneratedCloze(BaseModel):
    """
    Generated cloze sentence with a Vietnamese translation and hint.

    Attributes:
        sentence (str): The exercise sentence containing the target word or cloze blank.
        translation_vi (str): The Vietnamese translation of the source text.
        hint_vi (str): The Vietnamese hint for the missing word.
    """

    sentence: str = Field(..., min_length=1, max_length=1000)
    translation_vi: str = Field(default="", max_length=1000)
    hint_vi: str = Field(..., min_length=1, max_length=500)


class ReviewClozeResponse(GeneratedCloze):
    """
    Cloze exercise associated with a vocabulary entry and review attempt.

    Attributes:
        attempt_id (str): The client-provided identifier used to deduplicate a review
            attempt.
        vocabulary_id (int): The identifier of the vocabulary entry.
    """

    attempt_id: str
    vocabulary_id: int


class ReviewWordRequest(BaseModel):
    """
    Request to record a review rating and optional answer context.

    Attributes:
        attempt_id (str): The client-provided identifier used to deduplicate a review
            attempt.
        rating (ReviewRating): The selected review difficulty rating.
        mode (Optional[ReviewMode]): The selected practice mode.
        correct (Optional[bool]): Whether the submitted answer is correct, if recorded.
        used_hint (bool): Whether the user requested a hint during the attempt.
        revealed_answer (bool): Whether the correct answer was shown before submission.
        submitted_answer (Optional[str]): The answer text recorded with the review, if
            supplied.
        response_ms (Optional[int]): The time taken to answer in milliseconds, if
            supplied.
    """

    attempt_id: str = Field(..., min_length=1, max_length=100)
    rating: ReviewRating
    mode: Optional[ReviewMode] = None
    correct: Optional[bool] = None
    used_hint: bool = False
    revealed_answer: bool = False
    submitted_answer: Optional[str] = Field(default=None, max_length=500)
    response_ms: Optional[int] = Field(default=None, ge=0)


class ReviewWordSubmitRequest(ReviewWordRequest):
    """
    Review submission with an optional saved word-list identifier.

    Attributes:
        word_list_id (Optional[int]): The saved word list used to check ownership and
            word membership, if supplied.
    """

    word_list_id: Optional[int] = Field(default=None, ge=1)


class ReviewWordResponse(BaseModel):
    """
    Response containing the updated review state and next scheduled review.

    Attributes:
        vocabulary_id (int): The identifier of the vocabulary entry.
        attempt_id (str): The client-provided identifier used to deduplicate a review
            attempt.
        rating (ReviewRating): The selected review difficulty rating.
        status (str): The current lifecycle state.
        repetition_count (int): The number of repetitions recorded in the review state.
        interval_days (int): The review interval expressed in days.
        interval_seconds (int): The delay before the next review in seconds.
        next_review_at (datetime): The timestamp when the next review becomes due.
    """

    vocabulary_id: int
    attempt_id: str
    rating: ReviewRating
    status: str
    repetition_count: int
    interval_days: int
    interval_seconds: int
    next_review_at: datetime


class ReviewSessionStartRequest(BaseModel):
    """
    Request to start a review session with a scope and initial mode.

    Attributes:
        scope (ReviewScope): Whether to include due words or all words for review.
        initial_mode (ReviewMode): The practice mode selected when the review session
            starts.
    """

    scope: ReviewScope = ReviewScope.DUE
    initial_mode: ReviewMode = ReviewMode.FLASHCARD


class ReviewTopicSessionStartRequest(ReviewSessionStartRequest):
    """
    Review session request scoped to a vocabulary book and topic.

    Attributes:
        book_slug (str): The URL slug identifying the vocabulary book.
        topic_slug (str): The URL slug identifying the vocabulary topic.
    """

    book_slug: str = Field(..., min_length=1)
    topic_slug: str = Field(..., min_length=1)


class ReviewSessionItemResponse(BaseModel):
    """
    Response tracking one vocabulary item's position and completion in a session.

    Attributes:
        vocabulary_id (int): The identifier of the vocabulary entry.
        order_num (int): The item's ordering position within its topic or session.
        completed_at (Optional[datetime]): The completion timestamp, or None while
            unfinished.
        last_attempt_id (Optional[str]): The identifier of the most recent recorded
            attempt, if any.
    """

    vocabulary_id: int
    order_num: int
    completed_at: Optional[datetime]
    last_attempt_id: Optional[str]


class ReviewSessionResponse(BaseModel):
    """
    Response containing review session progress and its ordered vocabulary items.

    Attributes:
        id (int): The unique record identifier.
        topic_slug (str): The URL slug identifying the vocabulary topic.
        scope (ReviewScope): Whether to include due words or all words for review.
        initial_mode (ReviewMode): The practice mode selected when the review session
            starts.
        status (str): The current lifecycle state.
        current_position (int): The current position within the ordered session items.
        total_items (int): The total number of vocabulary items in the session.
        started_at (datetime): The timestamp when the session started.
        completed_at (Optional[datetime]): The completion timestamp, or None while
            unfinished.
        items (List[ReviewSessionItemResponse]): The ordered vocabulary items included
            in the response.
    """

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
    """
    Request to record a vocabulary attempt within a review session.

    Attributes:
        vocabulary_id (int): The identifier of the vocabulary entry.
        attempt_id (str): The client-provided identifier used to deduplicate a review
            attempt.
        mode (ReviewMode): The selected practice mode.
        rating (Optional[ReviewRating]): The selected review difficulty rating.
        answer (Optional[str]): The submitted answer text, if supplied.
        correct (Optional[bool]): Whether the submitted answer is correct, if recorded.
        used_hint (bool): Whether the user requested a hint during the attempt.
        revealed_answer (bool): Whether the correct answer was shown before submission.
        response_ms (Optional[int]): The time taken to answer in milliseconds, if
            supplied.
    """

    vocabulary_id: int
    attempt_id: str = Field(..., min_length=1, max_length=100)
    mode: ReviewMode
    rating: Optional[ReviewRating] = None
    answer: Optional[str] = Field(default=None, max_length=500)
    correct: Optional[bool] = None
    used_hint: bool = False
    revealed_answer: bool = False
    response_ms: Optional[int] = Field(default=None, ge=0)
