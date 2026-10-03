from datetime import datetime, time, timedelta, timezone
import json
import re
from typing import List, Optional
from zoneinfo import ZoneInfo

from cachetools import TTLCache
from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_record,
    async_get_many_records_by,
    async_get_one_record_by,
    async_update_one_record,
    transactional,
)
from app.features.preferences.service import UserPreferencesService
from app.features.review.model import (
    ReviewAttempt,
    ReviewProgress,
    ReviewSession,
    ReviewSessionItem,
)
from app.features.review.schemas import (
    ReviewClozeResponse,
    GeneratedCloze,
    ReviewCheckRequest,
    ReviewCheckResponse,
    ReviewQueueResponse,
    ReviewItemResponse,
    ReviewSessionItemResponse,
    ReviewSessionResponse,
    ReviewSessionAttemptRequest,
    ReviewSessionStartRequest,
    ReviewSummaryResponse,
    ReviewOptionResponse,
    ReviewWordRequest,
    ReviewWordResponse,
)
from app.features.review.srs import (
    ReviewProgressState,
    build_review_options,
    calculate_review_schedule,
)
from app.features.vocabulary.model import (
    Vocabulary,
    VocabularyBook,
    VocabularyTopic,
    VocabularyTopicWord,
)
from app.features.vocabulary.queries import get_topic_words_with_progress
from app.utils.ai_client import call_ai
from app.utils.constants import ReviewScope, ReviewRating, ReviewMode, WordStatus


_CLOZE_CACHE: TTLCache = TTLCache(maxsize=1000, ttl=1800)


class ReviewService(object):
    """Handle vocabulary review queues, attempts, and sessions."""

    @staticmethod
    async def get_review_summary(
        user_id: int,
        session: AsyncSession,
    ) -> ReviewSummaryResponse:
        """
        Summarize due vocabulary and today's new-word goal for one user.

        Args:
            user_id (int): The ID of the user.
            session (AsyncSession): The database session.

        Returns:
            ReviewSummaryResponse: Summary of due words and daily progress.
        """
        preferences = await UserPreferencesService.get_preferences(user_id, session)
        user_timezone = ZoneInfo(preferences.timezone)
        now = datetime.now(user_timezone)
        now_utc = now.astimezone(timezone.utc)
        day_start = datetime.combine(now.date(), time.min, tzinfo=user_timezone)
        next_day_start = datetime.combine(
            now.date() + timedelta(days=1),
            time.min,
            tzinfo=user_timezone,
        )
        day_start_utc = day_start.astimezone(timezone.utc)
        next_day_start_utc = next_day_start.astimezone(timezone.utc)

        due_word_count = (
            await session.exec(
                select(func.count(ReviewProgress.id)).where(
                    ReviewProgress.user_id == user_id,
                    ReviewProgress.status.notin_(
                        [WordStatus.NEW.value, WordStatus.IGNORED.value]
                    ),
                    or_(
                        ReviewProgress.next_review_at <= now_utc,
                        and_(
                            ReviewProgress.next_review_at.is_(None),
                            ReviewProgress.status == WordStatus.LEARNING.value,
                        ),
                    ),
                )
            )
        ).one()

        new_words_learned_today = (
            await session.exec(
                select(func.count(func.distinct(ReviewAttempt.review_progress_id)))
                .join(ReviewProgress)
                .where(
                    ReviewProgress.user_id == user_id,
                    ReviewAttempt.reviewed_at >= day_start_utc,
                    ReviewAttempt.reviewed_at < next_day_start_utc,
                    ~select(ReviewAttempt.id)
                    .where(
                        ReviewAttempt.review_progress_id
                        == ReviewProgress.id,
                        ReviewAttempt.reviewed_at < day_start_utc,
                    )
                    .correlate(ReviewProgress)
                    .exists(),
                )
            )
        ).one()

        return ReviewSummaryResponse(
            due_word_count=due_word_count,
            daily_new_word_target=preferences.daily_new_words,
            new_words_learned_today=new_words_learned_today,
            remaining_new_words=max(
                0, preferences.daily_new_words - new_words_learned_today
            ),
        )

    @staticmethod
    def _state(progress: Optional[ReviewProgress]) -> ReviewProgressState:
        """Convert persisted progress into the pure SRS state model."""
        if not progress:
            return ReviewProgressState()
        return ReviewProgressState(
            repetition_count=progress.repetition_count,
            interval_days=progress.interval_days,
            ease_factor=float(progress.ease_factor),
        )

    @staticmethod
    def _review_options(
        progress: Optional[ReviewProgress], 
        reviewed_at: datetime
    ) -> List[ReviewOptionResponse]:
        """Build the review options for all supported ratings."""
        return [
            ReviewOptionResponse(
                rating=rating,
                interval_seconds=schedule.interval_seconds,
                next_review_at=schedule.next_review_at,
            )
            for rating, schedule in build_review_options(ReviewService._state(progress), reviewed_at).items()
        ]

    @staticmethod
    async def _get_topic(
        book_slug: str, 
        topic_slug: str, 
        session: AsyncSession
    ) -> VocabularyTopic:
        """Load an active vocabulary topic belonging to a book.

        Args:
            book_slug (str): URL slug of the vocabulary book.
            topic_slug (str): URL slug of the vocabulary topic.
            session (AsyncSession): Active database session.

        Returns:
            VocabularyTopic: The matching active topic.

        Raises:
            HTTPException: If the topic is not found in the active book.
        """
        return await async_get_one_record_by(
            VocabularyTopic,
            [
                VocabularyTopic.slug == topic_slug,
                VocabularyTopic.book.has(
                    and_(
                        VocabularyBook.slug == book_slug,
                        VocabularyBook.deleted.is_(False),
                    )
                ),
            ],
            session,
            not_found_msg="Vocabulary topic not found",
            raise_if_not_found=True,
        )

    @staticmethod
    async def ensure_topic_vocabulary(
        book_slug: str,
        topic_slug: str,
        vocabulary_id: int,
        session: AsyncSession,
    ) -> None:
        """Ensure a vocabulary entry belongs to the requested active topic.

        Args:
            book_slug (str): URL slug of the vocabulary book.
            topic_slug (str): URL slug of the vocabulary topic.
            vocabulary_id (int): Identifier of the vocabulary entry.
            session (AsyncSession): Active database session.

        Raises:
            HTTPException: If the topic or vocabulary entry is not found.
        """
        topic = await ReviewService._get_topic(book_slug, topic_slug, session)
        linked = await async_get_one_record_by(
            VocabularyTopicWord,
            [
                VocabularyTopicWord.topic_id == topic.id,
                VocabularyTopicWord.vocabulary_id == vocabulary_id,
            ],
            session,
            raise_if_not_found=False,
        )

        if linked is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vocabulary word not found in topic",
            )

    @staticmethod
    async def _load_deck(
        user_id: int,
        book_slug: str,
        topic_slug: str,
        mode: ReviewMode,
        scope: ReviewScope,
        session: AsyncSession,
    ) -> tuple[VocabularyTopic, ReviewQueueResponse]:
        """Load a review queue together with its vocabulary topic.

        Args:
            user_id (int): Identifier of the authenticated user.
            book_slug (str): URL slug of the vocabulary book.
            topic_slug (str): URL slug of the vocabulary topic.
            mode (ReviewMode): Review mode.
            scope (ReviewScope): Whether to include due words or all words.
            session (AsyncSession): Active database session.

        Returns:
            tuple[VocabularyTopic, ReviewQueueResponse]: The topic and deck.

        Raises:
            HTTPException: If the requested topic cannot be found.
        """
        topic = await ReviewService._get_topic(book_slug, topic_slug, session)

        rows = await get_topic_words_with_progress(topic.id, user_id, session)
    
        now = datetime.now(timezone.utc)
        classified = []
        for vocab, topic_word, progress in rows:
            if not progress or progress.status == WordStatus.NEW.value:
                progress_status = "new"
            elif progress.status == WordStatus.IGNORED.value:
                progress_status = "ignored"
            elif not progress.next_review_at: 
                progress_status = (
                    "due"
                    if progress.status == WordStatus.LEARNING.value
                    else "future"
                )
            else:
                review_at = progress.next_review_at
                compare_now = now
                if review_at.tzinfo is None and now.tzinfo is not None:
                    compare_now = now.replace(tzinfo=None)

                if review_at < compare_now:
                    progress_status = "overdue"
                elif review_at == compare_now:
                    progress_status = "due"
                else:
                    progress_status = "future"

            classified.append((vocab, topic_word, progress, progress_status))

        allowed = {"overdue", "due", "new"}

        if scope != ReviewScope.DUE:
            allowed.add("future")

        classified = [row for row in classified if row[3] in allowed]
        priority = {
            "overdue": 0,
            "due": 1,
            "new": 2,
            "future": 3,
        }
        classified.sort(
            key=lambda row: (
                priority[row[3]],
                row[1].order_num,
                row[0].id,
            )
        )

        items = [
            ReviewItemResponse(
                vocabulary_id=vocab.id,
                word=vocab.word,
                word_type=vocab.word_type,
                ipa=vocab.ipa,
                audio_url=vocab.audio_url,
                image_url=vocab.image_url,
                definition_vi=vocab.definition_vi,
                example_sentence=vocab.example_sentence,
                example_translation_vi=vocab.example_translation_vi,
                order_num=topic_word.order_num,
                status=progress.status if progress else WordStatus.NEW.value,
                review_options=ReviewService._review_options(progress, now),
            )
            for vocab, topic_word, progress, _ in classified
        ]
        return topic, ReviewQueueResponse(
            topic_slug=topic.slug,
            mode=mode,
            scope=scope,
            total_word_count=len(items),
            due_count=sum(
                row[3] in {"overdue", "due"}
                for row in classified
            ),
            new_count=sum(
                row[3] == "new"
                for row in classified
            ),
            items=items,
        )

    @staticmethod
    async def get_review_queue(
        user_id: int,
        book_slug: str,
        topic_slug: str,
        mode: ReviewMode,
        scope: ReviewScope,
        session: AsyncSession,
    ) -> ReviewQueueResponse:
        """Return vocabulary items available for the requested review scope.

        Args:
            user_id (int): Identifier of the authenticated user.
            book_slug (str): URL slug of the vocabulary book.
            topic_slug (str): URL slug of the vocabulary topic.
            mode (ReviewMode): Review mode.
            scope (ReviewScope): Whether to include due words or all words.
            session (AsyncSession): Active database session.

        Returns:
            ReviewQueueResponse: The ordered vocabulary review queue.

        Raises:
            HTTPException: If the requested topic cannot be found.
        """
        _, deck = await ReviewService._load_deck(
            user_id,
            book_slug,
            topic_slug,
            mode,
            scope,
            session,
        )
        return deck

    @staticmethod
    async def _get_vocab_and_progress(
        user_id: int,
        vocabulary_id: int,
        session: AsyncSession,
    ) -> tuple[Vocabulary, Optional[ReviewProgress]]:
        """Load a vocabulary entry and its optional user-specific progress.

        Args:
            user_id (int): Identifier of the authenticated user.
            vocabulary_id (int): Identifier of the vocabulary entry.
            session (AsyncSession): Active database session.

        Returns:
            tuple[Vocabulary, Optional[ReviewProgress]]: Vocabulary and progress.

        Raises:
            HTTPException: If the vocabulary entry does not exist.
        """
        vocab = await async_get_one_record_by(
            Vocabulary,
            [Vocabulary.id == vocabulary_id],
            session,
            raise_if_not_found=False,
        )
        if vocab is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Vocabulary word not found"
            )
        progress = await async_get_one_record_by(
            ReviewProgress,
            [
                ReviewProgress.user_id == user_id,
                ReviewProgress.vocabulary_id == vocabulary_id,
            ],
            session,
            raise_if_not_found=False,
        )
        return vocab, progress

    @staticmethod
    async def _get_review_session(
        user_id: int,
        session_id: int,
        session: AsyncSession,
    ) -> ReviewSession:
        """Load a user's review session with its topic and queued items.

        Args:
            user_id (int): Identifier of the authenticated user.
            session_id (int): Identifier of the review session.
            session (AsyncSession): Active database session.

        Returns:
            ReviewSession: The matching review session.

        Raises:
            HTTPException: If the session does not belong to the user.
        """
        return await async_get_one_record_by(
            ReviewSession,
            [
                ReviewSession.id == session_id,
                ReviewSession.user_id == user_id,
            ],
            session,
            options=[
                selectinload(ReviewSession.topic),
                selectinload(ReviewSession.items),
            ],
                not_found_msg="Review session not found",
            raise_if_not_found=True,
        )

    @staticmethod
    async def check_answer(
        user_id: int,
        vocabulary_id: int,
        data: ReviewCheckRequest,
        session: AsyncSession,
    ) -> ReviewCheckResponse:
        """Check a typing answer and return the available review options.

        Args:
            user_id (int): Identifier of the authenticated user.
            vocabulary_id (int): Identifier of the vocabulary entry.
            data (ReviewCheckRequest): Submitted answer data.
            session (AsyncSession): Active database session.

        Returns:
            ReviewCheckResponse: Answer result and review options.

        Raises:
            HTTPException: If the vocabulary entry does not exist.
        """
        now = datetime.now(timezone.utc)

        vocab, progress = await ReviewService._get_vocab_and_progress(
            user_id,
            vocabulary_id,
            session,
        )
        correct = data.answer.strip().lower() == vocab.word.strip().lower()
        options = ReviewService._review_options(progress, now)
        return ReviewCheckResponse(
            attempt_id=data.attempt_id,
            correct=correct,
            correct_answer=vocab.word,
            review_options={option.rating.value: option for option in options},
        )

    @staticmethod
    def _prepare_cloze(raw: GeneratedCloze, target: str) -> Optional[GeneratedCloze]:
        pattern = re.compile(rf"(?<!\w){re.escape(target)}(?!\w)", re.IGNORECASE)
        if len(pattern.findall(raw.sentence)) != 1:
            return None
        return raw.model_copy(
            update={"sentence": pattern.sub("_____", raw.sentence, count=1)}
        )

    @staticmethod
    async def generate_cloze(
        user_id: int,
        vocabulary_id: int,
        attempt_id: str,
        session: AsyncSession,
    ) -> ReviewClozeResponse:
        """Generate and cache a cloze exercise for a vocabulary entry.

        Args:
            user_id (int): Identifier of the authenticated user.
            vocabulary_id (int): Identifier of the vocabulary entry.
            attempt_id (str): Client-generated identifier for the attempt.
            session (AsyncSession): Active database session.

        Returns:
            ReviewClozeResponse: The generated exercise with the target hidden.

        Raises:
            HTTPException: If the vocabulary or cloze exercise is unavailable.
        """
        cache_key = (user_id, vocabulary_id, attempt_id)

        if cached := _CLOZE_CACHE.get(cache_key):
            return cached

        vocab, _ = await ReviewService._get_vocab_and_progress(
            user_id,
            vocabulary_id,
            session,
        )

        generated = None

        try:
            raw = await call_ai(
                prompt=(
                    f'Create one English cloze sentence using the exact '
                    f'target word "{vocab.word}" once. '
                    "Return JSON only with sentence, translation_vi, and hint_vi. "
                    "Keep the sentence under 160 characters."
                ),
                system_prompt=(
                    "You generate concise vocabulary exercises. "
                    "Return valid JSON only."
                ),
                max_tokens=300,
                service_name="cloze",
            )

            raw = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                raw.strip(),
                flags=re.IGNORECASE,
            ).strip()

            generated = ReviewService._prepare_cloze(
                GeneratedCloze.model_validate(json.loads(raw)), vocab.word
            )

        except Exception:
            pass

        if not generated and vocab.example_sentence:
            fallback = GeneratedCloze(
                sentence=vocab.example_sentence,
                translation_vi=vocab.example_translation_vi or "",
                hint_vi=vocab.definition_vi or vocab.word,
            )
            generated = ReviewService._prepare_cloze(fallback, vocab.word)

        if not generated:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to create a cloze exercise",
            )

        response = ReviewClozeResponse(
            attempt_id=attempt_id,
            vocabulary_id=vocabulary_id,
            **generated.model_dump(),
        )

        _CLOZE_CACHE[cache_key] = response
        return response

    @staticmethod
    async def _review_word(
        user_id: int,
        vocabulary_id: int,
        data: ReviewWordRequest,
        session: AsyncSession,
    ) -> ReviewWordResponse:
        """Apply one vocabulary review inside the caller's transaction.

        Args:
            user_id (int): Identifier of the authenticated user.
            vocabulary_id (int): Identifier of the reviewed vocabulary entry.
            data (ReviewWordRequest): Review result and attempt metadata.
            session (AsyncSession): Active database session.

        Returns:
            ReviewWordResponse: The updated review state.

        Raises:
            HTTPException: If the vocabulary or attempt is invalid.
        """
        attempt = await async_get_one_record_by(
            ReviewAttempt,
            [ReviewAttempt.attempt_id == data.attempt_id],
            session,
            options=[joinedload(ReviewAttempt.review_progress, innerjoin=True)],
            raise_if_not_found=False,
        )

        if attempt:
            progress = attempt.review_progress

            if progress.user_id != user_id or progress.vocabulary_id != vocabulary_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="attempt_id belongs to another review",
                )

            return ReviewService._review_response(
                vocabulary_id,
                attempt.attempt_id,
                attempt.rating,
                progress,
                attempt.reviewed_at,
            )

        vocab, progress = await ReviewService._get_vocab_and_progress(user_id, vocabulary_id, session)

        if not progress:
            progress = await async_create_record(
                ReviewProgress,
                {
                    "user_id": user_id,
                    "vocabulary_id": vocabulary_id,
                },
                session,
            )

        now = datetime.now(timezone.utc)

        schedule = calculate_review_schedule(
            ReviewService._state(progress),
            data.rating,
            now,
        )

        progress = await async_update_one_record(
            ReviewProgress,
            progress.id,
            {
                "repetition_count": schedule.repetition_count,
                "interval_days": schedule.interval_days,
                "ease_factor": schedule.ease_factor,
                "next_review_at": schedule.next_review_at,
                "status": schedule.status,
                "last_reviewed_at": now,
            },
            session,
        )

        await async_create_record(
            ReviewAttempt,
            {
                "review_progress_id": progress.id,
                "attempt_id": data.attempt_id,
                "mode": data.mode.value if data.mode else None,
                "correct": data.correct,
                "used_hint": data.used_hint,
                "revealed_answer": data.revealed_answer,
                "submitted_answer": data.submitted_answer,
                "response_ms": data.response_ms,
                "rating": data.rating.value,
                "reviewed_at": now,
            },
            session,
        )

        return ReviewService._review_response(
            vocab.id,
            data.attempt_id,
            data.rating.value,
            progress,
            now,
        )

    @staticmethod
    @transactional()
    async def record_review(
        user_id: int,
        vocabulary_id: int,
        data: ReviewWordRequest,
        session: AsyncSession,
    ) -> ReviewWordResponse:
        """Record a vocabulary review as a single database transaction.

        Args:
            user_id (int): Identifier of the authenticated user.
            vocabulary_id (int): Identifier of the reviewed vocabulary entry.
            data (ReviewWordRequest): Review result and attempt metadata.
            session (AsyncSession): Active database session.

        Returns:
            ReviewWordResponse: The updated review state.

        Raises:
            HTTPException: If the vocabulary or attempt is invalid.
        """
        return await ReviewService._review_word(user_id, vocabulary_id, data, session)

    @staticmethod
    def _review_response(
        vocabulary_id: int,
        attempt_id: str,
        rating: str,
        progress: ReviewProgress,
        reviewed_at: datetime,
    ) -> ReviewWordResponse:
        """
        Build the public response from persisted review progress.

        Args:
            vocabulary_id (int): Identifier of the reviewed vocabulary entry.
            attempt_id (str): Client-generated attempt identifier.
            rating (str): Stored review rating value.
            progress (ReviewProgress): Updated vocabulary progress.
            reviewed_at (datetime): Timestamp of the review.

        Returns:
            ReviewWordResponse: The updated review state.
        """
        rating = ReviewRating(rating)

        schedule = calculate_review_schedule(
            ReviewService._state(progress),
            rating,
            reviewed_at,
        )

        interval_seconds = (
            int(
                (
                    progress.next_review_at
                    - (progress.last_reviewed_at or reviewed_at)
                ).total_seconds()
            )
            if progress.next_review_at
            else schedule.interval_seconds
        )

        return ReviewWordResponse(
            vocabulary_id=vocabulary_id,
            attempt_id=attempt_id,
            rating=rating,
            status=progress.status,
            repetition_count=progress.repetition_count,
            interval_days=progress.interval_days,
            interval_seconds=interval_seconds,
            next_review_at=progress.next_review_at,
        )

    @staticmethod
    @transactional()
    async def start_review_session(
        user_id: int,
        book_slug: str,
        topic_slug: str,
        data: ReviewSessionStartRequest,
        session: AsyncSession,
    ) -> ReviewSessionResponse:
        """Create a fixed review queue from the current topic.

        Args:
            user_id (int): Identifier of the authenticated user.
            book_slug (str): URL slug of the vocabulary book.
            topic_slug (str): URL slug of the vocabulary topic.
            data (ReviewSessionStartRequest): Session scope and initial mode.
            session (AsyncSession): Active database session.

        Returns:
            ReviewSessionResponse: The newly created review session.

        Raises:
            HTTPException: If the topic is not found or the deck is empty.
        """
        topic, deck = await ReviewService._load_deck(
            user_id,
            book_slug,
            topic_slug,
            data.initial_mode,
            data.scope,
            session,
        )

        if not deck.items:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "No vocabulary words are available "
                    "for this review scope"
                ),
            )

        review_session = await async_create_record(
            ReviewSession,
            {
                "user_id": user_id,
                "topic_id": topic.id,
                "scope": data.scope.value,
                "initial_mode": data.initial_mode.value,
                "status": "started",
                "current_position": 0,
                "total_items": len(deck.items),
                "started_at": datetime.now(timezone.utc),
                "topic": topic,
                "items": [
                    ReviewSessionItem(
                        vocabulary_id=item.vocabulary_id,
                        order_num=index,
                    )
                    for index, item in enumerate(deck.items)
                ],
            },
            session,
        )

        return ReviewService._session_response(review_session)

    @staticmethod
    async def get_review_session(
        user_id: int,
        session_id: int,
        session: AsyncSession,
    ) -> ReviewSessionResponse:
        """Return one review session owned by the current user.

        Args:
            user_id (int): Identifier of the authenticated user.
            session_id (int): Identifier of the review session.
            session (AsyncSession): Active database session.

        Returns:
            ReviewSessionResponse: The current session state.

        Raises:
            HTTPException: If the session does not belong to the user.
        """
        review_session = await ReviewService._get_review_session(
            user_id,
            session_id,
            session,
        )

        return ReviewService._session_response(review_session)

    @staticmethod
    @transactional()
    async def complete_review_session(
        user_id: int,
        session_id: int,
        session: AsyncSession,
    ) -> ReviewSessionResponse:
        """Mark a user's review session as completed.

        Args:
            user_id (int): Identifier of the authenticated user.
            session_id (int): Identifier of the review session.
            session (AsyncSession): Active database session.

        Returns:
            ReviewSessionResponse: The completed session state.

        Raises:
            HTTPException: If the session does not belong to the user.
        """
        review_session = await ReviewService._get_review_session(
            user_id,
            session_id,
            session,
        )

        if review_session.status != "completed":
            review_session.status = "completed"
            review_session.completed_at = datetime.now(timezone.utc)
            review_session.current_position = (
                review_session.total_items
            )
        return ReviewService._session_response(review_session)

    @staticmethod
    @transactional()
    async def record_review_attempt(
        user_id: int,
        session_id: int,
        data: ReviewSessionAttemptRequest,
        session: AsyncSession,
    ) -> ReviewSessionResponse:
        """Record an item attempt and update the session position.

        Args:
            user_id (int): Identifier of the authenticated user.
            session_id (int): Identifier of the review session.
            data (ReviewSessionAttemptRequest): Submitted attempt data.
            session (AsyncSession): Active database session.

        Returns:
            ReviewSessionResponse: The updated session state.

        Raises:
            HTTPException: If the session is complete or the word is not queued.
        """
        review_session = await ReviewService._get_review_session(
            user_id,
            session_id,
            session,
        )

        if review_session.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Review session is already completed",
            )

        item = next(
            (
                item
                for item in review_session.items
                if item.vocabulary_id == data.vocabulary_id
            ),
            None,
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vocabulary word is not in this session",
            )

        if data.rating is not None:
            await ReviewService._review_word(
                user_id,
                data.vocabulary_id,
                ReviewWordRequest(
                    attempt_id=data.attempt_id,
                    rating=data.rating,
                    mode=data.mode,
                    correct=data.correct,
                    used_hint=data.used_hint,
                    revealed_answer=data.revealed_answer,
                    submitted_answer=data.answer,
                    response_ms=data.response_ms,
                ),
                session,
            )

        item.completed_at = item.completed_at or datetime.now(timezone.utc)
        item.last_attempt_id = data.attempt_id

        review_session.current_position = sum(bool(item.completed_at) for item in review_session.items)

        return ReviewService._session_response(review_session)

    @staticmethod
    def _session_response(
        review_session: ReviewSession,
    ) -> ReviewSessionResponse:
        """
        Convert a persisted review session into its API response.

        Args:
            review_session (ReviewSession): The persisted review session.   

        Returns:
            ReviewSessionResponse: The API response representation of the session.
        """
        return ReviewSessionResponse(
            id=review_session.id,
            topic_slug=(
                review_session.topic.slug
                if review_session.topic
                else ""
            ),
            scope=ReviewScope(review_session.scope),
            initial_mode=ReviewMode(
                review_session.initial_mode
            ),
            status=review_session.status,
            current_position=review_session.current_position,
            total_items=review_session.total_items,
            started_at=review_session.started_at,
            completed_at=review_session.completed_at,
            items=[
                ReviewSessionItemResponse(
                    vocabulary_id=item.vocabulary_id,
                    order_num=item.order_num,
                    completed_at=item.completed_at,
                    last_attempt_id=item.last_attempt_id,
                )
                for item in review_session.items
            ],
        )
