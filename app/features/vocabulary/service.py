from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import case, func
from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_record,
    async_get_many_records_by,
    async_get_one_record_by,
    async_update_one_record,
    transactional,
)
from app.features.vocabulary.model import (
    Notebook,
    NotebookItem,
    Vocabulary,
    VocabularyBook,
    VocabularyProgress,
    VocabularyReviewLog,
    VocabularyTopic,
    VocabularyTopicWord,
)
from app.features.vocabulary.schemas import (
    NotebookVocabularyItemResponse,
    TopicWordResponse,
    VocabularyItemResponse,
    VocabularyListFilter,
    VocabularySaveRequest,
    VocabularyTopicResponse,
)
from app.utils.common import page_size_to_offset_limit
from app.utils.constants import ReviewRating, WordStatus


# ========================
# SIMPLE SPACED REPETITION
# ========================

_INTERVAL_STEPS = [1, 3, 7, 14, 30]
_LEARNING_REVIEWS_THRESHOLD = 2
_REVIEWING_MASTER_THRESHOLD = 5
_MASTER_INTERVAL_DAYS = 30

def _next_interval(repetition_count: int) -> int:
    """Return next review interval in days for successful reviews."""
    index = max(repetition_count - 1, 0)
    if index >= len(_INTERVAL_STEPS):
        return _INTERVAL_STEPS[-1]
    return _INTERVAL_STEPS[index]


# ========================
# HELPERS
# ========================


async def _sync_vocabulary(
    word: str, session: AsyncSession
) -> Vocabulary:
    """Find an existing vocabulary entry or create a new one."""
    normalized = word.strip().lower()
    vocabularies = await async_get_many_records_by(
        Vocabulary,
        [func.lower(Vocabulary.word) == normalized],
        session,
        raise_if_not_found=False,
    )
    if vocabularies:
        return next(
            (vocab for vocab in vocabularies if vocab.word_type is None),
            min(vocabularies, key=lambda vocab: vocab.created_time),
        )
    return await async_create_record(
        Vocabulary,
        {"word": normalized, "word_type": None, "definition_vi": None},
        session,
    )


async def _get_user_notebook(
    notebook_id: int, user_id: int, session: AsyncSession
) -> Notebook:
    """Validate notebook belongs to user and return it."""
    return await async_get_one_record_by(
        Notebook,
        [Notebook.id == notebook_id, Notebook.user_id == user_id],
        session,
        raise_if_not_found=True,
        not_found_msg="Notebook not found",
    )


# ========================
# RESPONSE BUILDERS
# ========================


def _build_vocabulary_response(
    vocab: Vocabulary,
    progress: VocabularyProgress,
) -> VocabularyItemResponse:
    """Build the response for a user's global vocabulary progress."""
    return VocabularyItemResponse(
        id=vocab.id,
        word=vocab.word,
        word_type=vocab.word_type,
        ipa=vocab.ipa,
        audio_url=vocab.audio_url,
        definition_vi=vocab.definition_vi,
        example_sentence=vocab.example_sentence,
        example_translation_vi=vocab.example_translation_vi,
        status=progress.status,
        repetition_count=progress.repetition_count,
        interval_days=progress.interval_days,
        next_review_at=progress.next_review_at,
        last_reviewed_at=progress.last_reviewed_at,
        personal_note=progress.personal_note,
        created_time=progress.created_time,
    )


def _build_notebook_vocabulary_response(
    vocab: Vocabulary,
    progress: VocabularyProgress,
    item: NotebookItem,
) -> NotebookVocabularyItemResponse:
    """Build the response for a vocabulary item saved in one notebook."""
    return NotebookVocabularyItemResponse(
        **_build_vocabulary_response(vocab, progress).model_dump(),
        notebook_item_id=item.id,
        notebook_id=item.notebook_id,
        context_sentence=item.context_sentence,
        note=item.note,
    )


def _build_topic_response(
    topic: VocabularyTopic,
    word_count: int,
    mastered_count: int,
    learning_count: int,
) -> VocabularyTopicResponse:
    """Build a VocabularyTopicResponse from model instances and progress counts."""
    return VocabularyTopicResponse(
        id=topic.id,
        book_id=topic.book_id,
        name=topic.name,
        slug=topic.slug,
        order_num=topic.order_num,
        word_count=word_count,
        mastered_word_count=mastered_count,
        learning_word_count=learning_count,
    )


def _build_topic_word_response(
    vocab: Vocabulary, order_num: int, progress: Optional[VocabularyProgress] = None
) -> TopicWordResponse:
    """Build a TopicWordResponse from vocabulary model and optional progress info."""
    return TopicWordResponse(
        id=vocab.id,
        word=vocab.word,
        word_type=vocab.word_type,
        ipa=vocab.ipa,
        audio_url=vocab.audio_url,
        image_url=vocab.image_url,
        definition_vi=vocab.definition_vi,
        example_sentence=vocab.example_sentence,
        example_translation_vi=vocab.example_translation_vi,
        order_num=order_num,
        status=progress.status if progress else None,
        repetition_count=progress.repetition_count if progress else 0,
        interval_days=progress.interval_days if progress else 0,
        next_review_at=progress.next_review_at if progress else None,
    )


# ========================
# VOCABULARY SERVICE
# ========================


class VocabularyService:
    """
    Service for managing user vocabulary, including saving words,
    listing saved words, and spaced repetition review.
    """

    @staticmethod
    @transactional()
    async def save_word(
        user_id: int,
        notebook_id: int,
        data: VocabularySaveRequest,
        session: AsyncSession,
    ) -> NotebookVocabularyItemResponse:
        """Save a word to the user's vocabulary notebook.

        Creates the vocabulary record if it doesn't exist globally,
        adds it to the specified notebook, and initializes
        a progress tracker for spaced repetition.
        """
        try:
            vocab = await _sync_vocabulary(data.word, session)
            notebook = await _get_user_notebook(notebook_id, user_id, session)

            item = await async_get_one_record_by(
                NotebookItem,
                [
                    NotebookItem.notebook_id == notebook.id,
                    NotebookItem.vocabulary_id == vocab.id,
                ],
                session,
                raise_if_not_found=False,
            )
            if not item:
                item = await async_create_record(
                    NotebookItem,
                    {
                        "notebook_id": notebook.id,
                        "vocabulary_id": vocab.id,
                        "context_sentence": data.context_sentence,
                        "note": data.note,
                    },
                    session,
                )
            elif data.context_sentence is not None or data.note is not None:
                update = {}
                if data.context_sentence is not None:
                    update["context_sentence"] = data.context_sentence
                if data.note is not None:
                    update["note"] = data.note
                item = await async_update_one_record(
                    NotebookItem, item.id, update, session
                )

            progress = await async_get_one_record_by(
                VocabularyProgress,
                [
                    VocabularyProgress.user_id == user_id,
                    VocabularyProgress.vocabulary_id == vocab.id,
                ],
                session,
                raise_if_not_found=False,
            )
            if not progress:
                progress = await async_create_record(
                    VocabularyProgress,
                    {
                        "user_id": user_id,
                        "vocabulary_id": vocab.id,
                    },
                    session,
                )

            return _build_notebook_vocabulary_response(vocab, progress, item)

        except Exception:
            await session.rollback()
            raise

    @staticmethod
    async def list_words(
        user_id: int,
        filters: VocabularyListFilter,
        session: AsyncSession,
    ) -> Tuple[List[VocabularyItemResponse], int, int]:
        """List the user's saved vocabulary with pagination and filtering.

        Supports filtering by learning status and keyword search
        against the word (ILIKE search).

        Args:
            user_id (int): The ID of the authenticated user.
            filters (VocabularyListFilter): Pagination and filter parameters.
            session (AsyncSession): The database session.

        Returns:
            Tuple[List[VocabularyItemResponse], int, int]: A tuple of
                vocabulary items, total count, and total pages.
        """
        conditions = [VocabularyProgress.user_id == user_id]

        if filters.status:
            conditions.append(VocabularyProgress.status == filters.status.value)
        if filters.keyword:
            kw = filters.keyword.strip()
            conditions.append(Vocabulary.word.ilike(f"%{kw}%"))

        total = (
            await session.exec(
                select(func.count(VocabularyProgress.id))
                .join(Vocabulary, VocabularyProgress.vocabulary_id == Vocabulary.id)
                .where(*conditions)
            )
        ).one()

        offset, limit = page_size_to_offset_limit(filters.page, filters.page_size)
        rows = (
            await session.exec(
                select(Vocabulary, VocabularyProgress)
                .join(Vocabulary, VocabularyProgress.vocabulary_id == Vocabulary.id)
                .where(*conditions)
                .order_by(VocabularyProgress.created_time.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        pages = -(-total // filters.page_size) if total else 0
        items = [_build_vocabulary_response(vocab, process) for vocab, process in rows]
        return items, total, pages

    @staticmethod
    @transactional()    
    async def review_word(
        user_id: int,
        vocabulary_id: int,
        rating: ReviewRating,
        session: AsyncSession,
    ) -> VocabularyItemResponse:
        """Review a vocabulary word and update its spaced repetition schedule.

        Uses a simple interval progression based on successful review count:
        day 1 -> 3 -> 7 -> 14 -> 30. If the user gets it wrong, the count
        resets and next review is back to 1 day.

        Args:
            user_id (int): The ID of the authenticated user.
            vocabulary_id (int): The vocabulary ID to review.
            rating (ReviewRating): The review result (correct or wrong).
            session (AsyncSession): The database session.

        Returns:
            VocabularyItemResponse: The updated vocabulary item.

        Raises:
            HTTPException 404: If the word is not in the user's vocabulary.
        """
        row = (
            await session.exec(
                select(VocabularyProgress, Vocabulary)
                .join(Vocabulary, VocabularyProgress.vocabulary_id == Vocabulary.id)
                .where(
                    VocabularyProgress.user_id == user_id,
                    VocabularyProgress.vocabulary_id == vocabulary_id,
                )
            )
        ).first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Word not found in your vocabulary",
            )
        progress, vocab = row

        now = datetime.now(timezone.utc)
        review_base = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if rating == ReviewRating.WRONG:
            rep_count = 0
            interval = 1
            new_status = WordStatus.LEARNING.value
        elif rating == ReviewRating.CORRECT:
            rep_count = progress.repetition_count + 1
            interval = _next_interval(rep_count)
            if rep_count >= _REVIEWING_MASTER_THRESHOLD and interval >= _MASTER_INTERVAL_DAYS:
                new_status = WordStatus.MASTERED.value
            elif rep_count >= _LEARNING_REVIEWS_THRESHOLD:
                new_status = WordStatus.REVIEWING.value
            else:
                new_status = progress.status

        try:
            progress = await async_update_one_record(
                VocabularyProgress,
                progress.id,
                {
                    "repetition_count": rep_count,
                    "interval_days": interval,
                    "last_reviewed_at": now,
                    "next_review_at": review_base + timedelta(days=interval),
                    "status": new_status,
                },
                session,
            )

            await async_create_record(
                VocabularyReviewLog,
                {
                    "vocabulary_progress_id": progress.id,
                    "rating": rating.value,
                    "reviewed_at": now,
                },
                session,
            )

            return _build_vocabulary_response(vocab, progress)

        except Exception:
            await session.rollback()
            raise

    @staticmethod
    async def get_due_words(
        user_id: int,
        session: AsyncSession,
        limit: int = 20,
    ) -> Tuple[List[VocabularyItemResponse], int]:
        """Get vocabulary words that are due for review.

        Words are considered due if their next_review_at is in the past
        or null. Results are ordered by next_review_at ascending (oldest
        first). Mastered and ignored words are excluded.

        Args:
            user_id (int): The ID of the authenticated user.
            session (AsyncSession): The database session.
            limit (int): Maximum number of words to return. Defaults to 20.

        Returns:
            Tuple[List[VocabularyItemResponse], int]: A tuple of
                due vocabulary items and the total number of due words.
        """
        now = datetime.now(timezone.utc)

        due_conditions = [
            VocabularyProgress.user_id == user_id,
            or_(
                VocabularyProgress.next_review_at <= now,
                VocabularyProgress.next_review_at.is_(None),
            ),
            VocabularyProgress.status != WordStatus.MASTERED.value,
            VocabularyProgress.status != WordStatus.IGNORED.value,
        ]

        total_due = (
            await session.exec(
                select(func.count(VocabularyProgress.id)).where(*due_conditions)
            )
        ).one()

        rows = (
            await session.exec(
                select(Vocabulary, VocabularyProgress)
                .join(Vocabulary, VocabularyProgress.vocabulary_id == Vocabulary.id)
                .where(*due_conditions)
                .order_by(VocabularyProgress.next_review_at.asc().nullsfirst())
                .limit(limit)
            )
        ).all()

        items = [_build_vocabulary_response(vocab, process) for vocab, process in rows]
        return items, total_due

    @staticmethod
    async def get_books(session: AsyncSession) -> List[VocabularyBook]:
        """Fetch all vocabulary books sorted by creation date."""
        return await async_get_many_records_by(
            VocabularyBook,
            [VocabularyBook.deleted.is_(False)],
            session,
            order_by=[VocabularyBook.created_time.asc()],
            raise_if_not_found=False,
        )

    @staticmethod
    async def get_book_topics(
        user_id: int, book_slug: str, session: AsyncSession
    ) -> List[VocabularyTopicResponse]:
        """Fetch topics for a vocabulary book with aggregated user progress stats."""
        book = await async_get_one_record_by(
            VocabularyBook,
            [VocabularyBook.slug == book_slug, VocabularyBook.deleted.is_(False)],
            session,
            raise_if_not_found=True,
            not_found_msg="Vocabulary book not found",
        )

        rows = (
            await session.exec(
                select(
                    VocabularyTopic,
                    func.count(VocabularyTopicWord.id).label("word_count"),
                    func.count(
                        case((VocabularyProgress.status == WordStatus.MASTERED.value, 1))
                    ).label("mastered_count"),
                    func.count(
                        case(
                            (
                                (VocabularyProgress.status == WordStatus.LEARNING.value)
                                | (VocabularyProgress.status == WordStatus.REVIEWING.value),
                                1,
                            )
                        )
                    ).label("learning_count"),
                )
                .where(VocabularyTopic.book_id == book.id)
                .join(
                    VocabularyTopicWord,
                    VocabularyTopic.id == VocabularyTopicWord.topic_id,
                    isouter=True,
                )
                .join(
                    VocabularyProgress,
                    (VocabularyProgress.vocabulary_id == VocabularyTopicWord.vocabulary_id)
                    & (VocabularyProgress.user_id == user_id),
                    isouter=True,
                )
                .group_by(VocabularyTopic.id)
                .order_by(VocabularyTopic.order_num.asc())
            )
        ).all()

        return [
            _build_topic_response(topic, word_count, mastered_count, learning_count)
            for topic, word_count, mastered_count, learning_count in rows
        ]

    @staticmethod
    async def get_topic_words(
        user_id: int, topic_slug: str, session: AsyncSession
    ) -> List[TopicWordResponse]:
        """Fetch all words in a topic with user's learning progress info."""
        topic = (
            await session.exec(
                select(VocabularyTopic)
                .join(VocabularyBook, VocabularyTopic.book_id == VocabularyBook.id)
                .where(
                    VocabularyTopic.slug == topic_slug,
                    VocabularyBook.deleted.is_(False),
                )
            )
        ).first()
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vocabulary topic not found",
            )

        rows = (
            await session.exec(
                select(Vocabulary, VocabularyTopicWord.order_num, VocabularyProgress)
                .join(VocabularyTopicWord, VocabularyTopicWord.vocabulary_id == Vocabulary.id)
                .join(
                    VocabularyProgress,
                    (VocabularyProgress.vocabulary_id == Vocabulary.id)
                    & (VocabularyProgress.user_id == user_id),
                    isouter=True,
                )
                .where(VocabularyTopicWord.topic_id == topic.id)
                .order_by(VocabularyTopicWord.order_num.asc())
            )
        ).all()

        return [
            _build_topic_word_response(vocab, order_num, progress)
            for vocab, order_num, progress in rows
        ]
