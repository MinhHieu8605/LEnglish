import json
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from cachetools import TTLCache
from sqlalchemy import and_
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_record,
    async_get_one_record_by,
    async_update_one_record,
    transactional,
)

from app.features.practice.model import (
    PracticeAttempt,
    PracticeProgress,
    PracticeSession,
    PracticeSessionItem,
)
from app.features.practice.schemas import (
    ClozePracticeResponse,
    GeneratedCloze,
    PracticeCheckRequest,
    PracticeCheckResponse,
    PracticeDeckResponse,
    PracticeItemResponse,
    PracticeSessionItemResponse,
    PracticeSessionResponse,
    PracticeSessionAttemptRequest,
    PracticeSessionStartRequest,
    ReviewOptionResponse,
    VocabularyReviewRequest,
    VocabularyReviewResponse,
)
from app.features.vocabulary.model import (
    Vocabulary,
    VocabularyBook,
    VocabularyTopic,
    VocabularyTopicWord,
)
from app.features.practice.srs import (
    PracticeProgressState,
    build_review_options,
    calculate_review_schedule,
)
from app.utils.ai_client import call_ai
from app.utils.constants import PracticeScope, ReviewRating, VocabularyDeckMode, WordStatus


_CLOZE_CACHE: TTLCache = TTLCache(maxsize=1000, ttl=1800)


def _state(progress: Optional[PracticeProgress]) -> PracticeProgressState:
    """Convert persisted progress into the pure SRS state model."""
    if not progress:
        return PracticeProgressState()
    return PracticeProgressState(
        repetition_count=progress.repetition_count,
        interval_days=progress.interval_days,
        ease_factor=float(progress.ease_factor),
    )


def _review_options(
    progress: Optional[PracticeProgress], 
    reviewed_at: datetime
) -> List[ReviewOptionResponse]:
    """Build the review options for all supported ratings."""
    return [
        ReviewOptionResponse(
            rating=rating,
            interval_seconds=schedule.interval_seconds,
            next_review_at=schedule.next_review_at,
        )
        for rating, schedule in build_review_options(_state(progress), reviewed_at).items()
    ]


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
    topic = await _get_topic(book_slug, topic_slug, session)
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


async def _load_deck(
    user_id: int,
    book_slug: str,
    topic_slug: str,
    mode: VocabularyDeckMode,
    scope: PracticeScope,
    session: AsyncSession,
) -> tuple[VocabularyTopic, PracticeDeckResponse]:
    """Load a practice deck together with the topic used to build it.

    Args:
        user_id (int): Identifier of the authenticated user.
        book_slug (str): URL slug of the vocabulary book.
        topic_slug (str): URL slug of the vocabulary topic.
        mode (VocabularyDeckMode): Initial practice mode.
        scope (PracticeScope): Whether to include only due words or all words.
        session (AsyncSession): Active database session.

    Returns:
        tuple[VocabularyTopic, PracticeDeckResponse]: The topic and deck.

    Raises:
        HTTPException: If the requested topic cannot be found.
    """
    topic = await _get_topic(book_slug, topic_slug, session)

    rows = (
        await session.exec(
            select(Vocabulary, VocabularyTopicWord, PracticeProgress)
            .join(
                VocabularyTopicWord, 
                VocabularyTopicWord.vocabulary_id == Vocabulary.id
            )
            .join(
                PracticeProgress,
                (PracticeProgress.vocabulary_id == Vocabulary.id)
                & (PracticeProgress.user_id == user_id),
                isouter=True,
            )
            .where(VocabularyTopicWord.topic_id == topic.id)
        )
    ).all()
    
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

    if scope != PracticeScope.DUE:
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
        PracticeItemResponse(
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
            review_options=_review_options(progress, now),
        )
        for vocab, topic_word, progress, _ in classified
    ]
    return topic, PracticeDeckResponse(
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


async def get_deck(
    user_id: int,
    book_slug: str,
    topic_slug: str,
    mode: VocabularyDeckMode,
    scope: PracticeScope,
    session: AsyncSession,
) -> PracticeDeckResponse:
    """Return the vocabulary items available for the requested practice scope.

    Args:
        user_id (int): Identifier of the authenticated user.
        book_slug (str): URL slug of the vocabulary book.
        topic_slug (str): URL slug of the vocabulary topic.
        mode (VocabularyDeckMode): Initial practice mode.
        scope (PracticeScope): Whether to include only due words or all words.
        session (AsyncSession): Active database session.

    Returns:
        PracticeDeckResponse: The ordered practice deck.

    Raises:
        HTTPException: If the requested topic cannot be found.
    """
    _, deck = await _load_deck(
        user_id,
        book_slug,
        topic_slug,
        mode,
        scope,
        session,
    )
    return deck


async def _get_vocab_and_progress(
    user_id: int,
    vocabulary_id: int,
    session: AsyncSession,
) -> tuple[Vocabulary, Optional[PracticeProgress]]:
    """Load a vocabulary entry and its optional user-specific progress.

    Args:
        user_id (int): Identifier of the authenticated user.
        vocabulary_id (int): Identifier of the vocabulary entry.
        session (AsyncSession): Active database session.

    Returns:
        tuple[Vocabulary, Optional[PracticeProgress]]: Vocabulary and progress.

    Raises:
        HTTPException: If the vocabulary entry does not exist.
    """
    row = (
        await session.exec(
            select(Vocabulary, PracticeProgress)
            .join(
                PracticeProgress,
                (PracticeProgress.vocabulary_id == Vocabulary.id)
                & (PracticeProgress.user_id == user_id),
                isouter=True,
            )
            .where(Vocabulary.id == vocabulary_id)
        )
    ).first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Vocabulary word not found"
        )
    return row


async def _get_practice_session(
    user_id: int,
    session_id: int,
    session: AsyncSession,
) -> PracticeSession:
    """Load a user's practice session with its topic and queued items.

    Args:
        user_id (int): Identifier of the authenticated user.
        session_id (int): Identifier of the practice session.
        session (AsyncSession): Active database session.

    Returns:
        PracticeSession: The matching practice session.

    Raises:
        HTTPException: If the session does not belong to the user.
    """
    return await async_get_one_record_by(
        PracticeSession,
        [
            PracticeSession.id == session_id,
            PracticeSession.user_id == user_id,
        ],
        session,
        options=[
            selectinload(PracticeSession.topic),
            selectinload(PracticeSession.items),
        ],
        not_found_msg="Practice session not found",
        raise_if_not_found=True,
    )


async def check_typing(
    user_id: int,
    vocabulary_id: int,
    data: PracticeCheckRequest,
    session: AsyncSession,
) -> PracticeCheckResponse:
    """Check a typing answer and return the available review options.

    Args:
        user_id (int): Identifier of the authenticated user.
        vocabulary_id (int): Identifier of the vocabulary entry.
        data (PracticeCheckRequest): Submitted answer data.
        session (AsyncSession): Active database session.

    Returns:
        PracticeCheckResponse: Answer result and review options.

    Raises:
        HTTPException: If the vocabulary entry does not exist.
    """
    now = datetime.now(timezone.utc)

    vocab, progress = await _get_vocab_and_progress(
        user_id,
        vocabulary_id,
        session,
    )
    correct = data.answer.strip().lower() == vocab.word.strip().lower()
    options = _review_options(progress, now)
    return PracticeCheckResponse(
        attempt_id=data.attempt_id,
        correct=correct,
        correct_answer=vocab.word,
        review_options={option.rating.value: option for option in options},
    )


def _target_pattern(target: str) -> re.Pattern:
    """Build a case-insensitive pattern for one complete target word."""
    return re.compile(rf"(?<!\w){re.escape(target)}(?!\w)", re.IGNORECASE)


def _validated_cloze(raw: GeneratedCloze, target: str) -> Optional[GeneratedCloze]:
    """Return a cloze only when the target appears exactly once."""
    if len(_target_pattern(target).findall(raw.sentence)) != 1:
        return None
    return raw


def _hide_target(cloze: GeneratedCloze, target: str) -> GeneratedCloze:
    """Replace the target word in a validated cloze with a blank."""
    sentence = _target_pattern(target).sub("_____", cloze.sentence, count=1)
    return GeneratedCloze(
        sentence=sentence,
        translation_vi=cloze.translation_vi,
        hint_vi=cloze.hint_vi,
    )


async def generate_cloze(
    user_id: int,
    vocabulary_id: int,
    attempt_id: str,
    session: AsyncSession,
) -> ClozePracticeResponse:
    """Generate and cache a cloze exercise for a vocabulary entry.

    Args:
        user_id (int): Identifier of the authenticated user.
        vocabulary_id (int): Identifier of the vocabulary entry.
        attempt_id (str): Client-generated identifier for the attempt.
        session (AsyncSession): Active database session.

    Returns:
        ClozePracticeResponse: The generated exercise with the target hidden.

    Raises:
        HTTPException: If the vocabulary or cloze exercise is unavailable.
    """
    cache_key = (user_id, vocabulary_id, attempt_id)

    if cached := _CLOZE_CACHE.get(cache_key):
        return cached

    vocab, _ = await _get_vocab_and_progress(
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

        generated = _validated_cloze(
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
        generated = _validated_cloze(fallback, vocab.word)

    if not generated:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to create a cloze exercise",
        )

    response = ClozePracticeResponse(
        attempt_id=attempt_id,
        vocabulary_id=vocabulary_id,
        **_hide_target(generated, vocab.word).model_dump(),
    )

    _CLOZE_CACHE[cache_key] = response
    return response


async def _review_vocabulary(
    user_id: int,
    vocabulary_id: int,
    data: VocabularyReviewRequest,
    session: AsyncSession,
) -> VocabularyReviewResponse:
    """Apply one vocabulary review inside the caller's transaction.

    Args:
        user_id (int): Identifier of the authenticated user.
        vocabulary_id (int): Identifier of the reviewed vocabulary entry.
        data (VocabularyReviewRequest): Review result and attempt metadata.
        session (AsyncSession): Active database session.

    Returns:
        VocabularyReviewResponse: The updated review state.

    Raises:
        HTTPException: If the vocabulary or attempt is invalid.
    """
    existing = (
        await session.exec(
            select(PracticeAttempt, PracticeProgress)
            .join(
                PracticeProgress,
                PracticeAttempt.practice_progress_id
                == PracticeProgress.id,
            )
            .where(
                PracticeAttempt.attempt_id == data.attempt_id,
                PracticeProgress.user_id == user_id,
            )
        )
    ).first()

    if existing:
        attempt, progress = existing

        if progress.vocabulary_id != vocabulary_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="attempt_id belongs to another vocabulary",
            )

        return _review_response(
            vocabulary_id,
            attempt.attempt_id,
            attempt.rating,
            progress,
            attempt.reviewed_at,
        )

    vocab, progress = await _get_vocab_and_progress(user_id, vocabulary_id, session)

    if not progress:
        progress = await async_create_record(
            PracticeProgress,
            {
                "user_id": user_id,
                "vocabulary_id": vocabulary_id,
            },
            session,
        )

    now = datetime.now(timezone.utc)

    schedule = calculate_review_schedule(
        _state(progress),
        data.rating,
        now,
    )

    progress = await async_update_one_record(
        PracticeProgress,
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
        PracticeAttempt,
        {
            "practice_progress_id": progress.id,
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

    return _review_response(
        vocab.id,
        data.attempt_id,
        data.rating.value,
        progress,
        now,
    )


@transactional()
async def review_vocabulary(
    user_id: int,
    vocabulary_id: int,
    data: VocabularyReviewRequest,
    session: AsyncSession,
) -> VocabularyReviewResponse:
    """Record a vocabulary review as a single database transaction.

    Args:
        user_id (int): Identifier of the authenticated user.
        vocabulary_id (int): Identifier of the reviewed vocabulary entry.
        data (VocabularyReviewRequest): Review result and attempt metadata.
        session (AsyncSession): Active database session.

    Returns:
        VocabularyReviewResponse: The updated review state.

    Raises:
        HTTPException: If the vocabulary or attempt is invalid.
    """
    return await _review_vocabulary(user_id, vocabulary_id, data, session)


def _review_response(
    vocabulary_id: int,
    attempt_id: str,
    rating: str,
    progress: PracticeProgress,
    reviewed_at: datetime,
) -> VocabularyReviewResponse:
    """
    Build the public response from persisted review progress.

    Args:
        vocabulary_id (int): Identifier of the reviewed vocabulary entry.
        attempt_id (str): Client-generated attempt identifier.
        rating (str): Stored review rating value.
        progress (PracticeProgress): Updated vocabulary progress.
        reviewed_at (datetime): Timestamp of the review.

    Returns:
        VocabularyReviewResponse: The updated review state.
    """
    rating = ReviewRating(rating)

    schedule = calculate_review_schedule(
        _state(progress),
        rating,
        reviewed_at,
    )

    interval_seconds = (
        int(
            (
                progress.next_review_at - reviewed_at
            ).total_seconds()
        )
        if progress.next_review_at
        else schedule.interval_seconds
    )

    return VocabularyReviewResponse(
        vocabulary_id=vocabulary_id,
        attempt_id=attempt_id,
        rating=rating,
        status=progress.status,
        repetition_count=progress.repetition_count,
        interval_days=progress.interval_days,
        interval_seconds=interval_seconds,
        next_review_at=progress.next_review_at,
    )


@transactional()
async def start_session(
    user_id: int,
    book_slug: str,
    topic_slug: str,
    data: PracticeSessionStartRequest,
    session: AsyncSession,
) -> PracticeSessionResponse:
    """Create a fixed practice queue from the current deck.

    Args:
        user_id (int): Identifier of the authenticated user.
        book_slug (str): URL slug of the vocabulary book.
        topic_slug (str): URL slug of the vocabulary topic.
        data (PracticeSessionStartRequest): Session scope and initial mode.
        session (AsyncSession): Active database session.

    Returns:
        PracticeSessionResponse: The newly created practice session.

    Raises:
        HTTPException: If the topic is not found or the deck is empty.
    """
    topic, deck = await _load_deck(
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
                "for this practice scope"
            ),
        )

    practice_session = PracticeSession(
        user_id=user_id,
        topic_id=topic.id,
        scope=data.scope.value,
        initial_mode=data.initial_mode.value,
        status="started",
        current_position=0,
        total_items=len(deck.items),
        started_at=datetime.now(timezone.utc),
        topic=topic,
        items=[
            PracticeSessionItem(
                vocabulary_id=item.vocabulary_id,
                order_num=index,
            )
            for index, item in enumerate(deck.items)
        ],
    )

    session.add(practice_session)
    await session.flush()

    return _session_response(practice_session)


async def get_session(
    user_id: int,
    session_id: int,
    session: AsyncSession,
) -> PracticeSessionResponse:
    """Return one practice session owned by the authenticated user.

    Args:
        user_id (int): Identifier of the authenticated user.
        session_id (int): Identifier of the practice session.
        session (AsyncSession): Active database session.

    Returns:
        PracticeSessionResponse: The current session state.

    Raises:
        HTTPException: If the session does not belong to the user.
    """
    practice_session = await _get_practice_session(
        user_id,
        session_id,
        session,
    )

    return _session_response(practice_session)


@transactional()
async def complete_session(
    user_id: int,
    session_id: int,
    session: AsyncSession,
) -> PracticeSessionResponse:
    """Mark a user's practice session as completed.

    Args:
        user_id (int): Identifier of the authenticated user.
        session_id (int): Identifier of the practice session.
        session (AsyncSession): Active database session.

    Returns:
        PracticeSessionResponse: The completed session state.

    Raises:
        HTTPException: If the session does not belong to the user.
    """
    practice_session = await _get_practice_session(
        user_id,
        session_id,
        session,
    )

    if practice_session.status != "completed":
        practice_session.status = "completed"
        practice_session.completed_at = datetime.now(timezone.utc)
        practice_session.current_position = (
            practice_session.total_items
        )
        await session.flush()

    return _session_response(practice_session)


@transactional()
async def record_session_attempt(
    user_id: int,
    session_id: int,
    data: PracticeSessionAttemptRequest,
    session: AsyncSession,
) -> PracticeSessionResponse:
    """Record an item attempt and update the session position.

    Args:
        user_id (int): Identifier of the authenticated user.
        session_id (int): Identifier of the practice session.
        data (PracticeSessionAttemptRequest): Submitted attempt data.
        session (AsyncSession): Active database session.

    Returns:
        PracticeSessionResponse: The updated session state.

    Raises:
        HTTPException: If the session is complete or the word is not queued.
    """
    practice_session = await _get_practice_session(
        user_id,
        session_id,
        session,
    )

    if practice_session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Practice session is already completed",
        )

    item = next(
        (
            item
            for item in practice_session.items
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
        await _review_vocabulary(
            user_id,
            data.vocabulary_id,
            VocabularyReviewRequest(
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

    practice_session.current_position = sum(
        bool(item.completed_at)
        for item in practice_session.items
    )

    await session.flush()

    return _session_response(practice_session)


def _session_response(
    practice_session: PracticeSession,
) -> PracticeSessionResponse:
    """Convert a persisted practice session into its API response."""
    return PracticeSessionResponse(
        id=practice_session.id,
        topic_slug=(
            practice_session.topic.slug
            if practice_session.topic
            else ""
        ),
        scope=PracticeScope(practice_session.scope),
        initial_mode=VocabularyDeckMode(
            practice_session.initial_mode
        ),
        status=practice_session.status,
        current_position=practice_session.current_position,
        total_items=practice_session.total_items,
        started_at=practice_session.started_at,
        completed_at=practice_session.completed_at,
        items=[
            PracticeSessionItemResponse(
                vocabulary_id=item.vocabulary_id,
                order_num=item.order_num,
                completed_at=item.completed_at,
                last_attempt_id=item.last_attempt_id,
            )
            for item in practice_session.items
        ],
    )
