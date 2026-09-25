from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_bulk_records,
    async_create_record,
    async_get_many_records_by,
    async_get_one_record_by,
    async_update_one_record,
    transactional,
)
from app.features.lesson.model import Subtitle
from app.features.vocabulary.model import (
    Vocabulary,
)
from app.features.practice.model import PracticeAttempt, PracticeProgress
from app.features.practice.srs import (
    PracticeProgressState,
    calculate_review_schedule,
)
from app.features.wordlist.model import Notebook, NotebookItem
from app.features.wordlist.schemas import (
    CreateWordListRequest,
    SavedWordFilter,
    SavedWordResponse,
    SavedWordReviewResponse,
    SavedWordsDueFilter,
    SaveWordRequest,
    WordListResponse,
)
from app.utils.common import page_size_to_offset_limit
from app.utils.constants import ReviewRating, WordStatus


def _calculate_srs_schedule(
    progress: PracticeProgress,
    rating: ReviewRating,
    reviewed_at: datetime,
) -> dict:
    """
    Calculate the next SRS state for a reviewed word.

    Args:
        progress (PracticeProgress): Current progress of the vocabulary.
        rating (ReviewRating): User-selected Again, Hard, Good, or Easy rating.
        reviewed_at (datetime): Time at which the review was submitted.

    Returns:
        dict: Fields used to update the vocabulary progress record.
    """
    schedule = calculate_review_schedule(
        PracticeProgressState(
            repetition_count=progress.repetition_count,
            interval_days=progress.interval_days,
            ease_factor=float(progress.ease_factor),
        ),
        rating,
        reviewed_at,
    )
    return {
        "repetition_count": schedule.repetition_count,
        "interval_days": schedule.interval_days,
        "ease_factor": schedule.ease_factor,
        "next_review_at": schedule.next_review_at,
        "status": schedule.status,
    }


async def _get_or_create_vocabularies(
    data: SaveWordRequest, session: AsyncSession
) -> List[Vocabulary]:
    """
    Get stored vocabulary entries or create a manually submitted word.

    Args:
        data (SaveWordRequest): Word and dictionary meanings to save.
        session (AsyncSession): Active database session.

    Returns:
        List[Vocabulary]: Existing or newly created entries for all word types.

    Raises:
        HTTPException: If a new word has no translation or dictionary meaning.
    """
    normalized = data.word.strip().lower()
    vocabularies = await async_get_many_records_by(
        Vocabulary,
        [func.lower(Vocabulary.word) == normalized],
        session,
        raise_if_not_found=False,
    )
    if vocabularies:
        return vocabularies

    meanings_by_type = {}
    for meaning in data.meanings:
        word_type = meaning.part_of_speech
        if word_type and meaning.definitions and word_type not in meanings_by_type:
            meanings_by_type[word_type] = meaning

    vocabulary_data = []
    for word_type, meaning in meanings_by_type.items():
        definition = meaning.definitions[0]
        vocabulary_data.append(
            {
                "word": normalized,
                "word_type": word_type,
                "ipa": meaning.ipa,
                "audio_url": meaning.audio_url,
                "image_url": data.image_url,
                "definition_vi": definition.definition_vi,
                "example_sentence": definition.example,
                "example_translation_vi": definition.example_vi,
                "source_subtitle_id": data.source_subtitle_id,
            }
        )

    if not vocabulary_data and data.translation_vi:
        vocabulary_data.append(
            {
                "word": normalized,
                "definition_vi": data.translation_vi,
                "image_url": data.image_url,
                "source_subtitle_id": data.source_subtitle_id,
            }
        )

    if not vocabulary_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A translation or dictionary meaning is required for a new word.",
        )

    return await async_create_bulk_records(Vocabulary, vocabulary_data, session)


async def _get_user_word_list(
    word_list_id: int, user_id: int, session: AsyncSession
) -> Notebook:
    """
    Get a word list owned by the authenticated user.

    Args:
        word_list_id (int): Identifier of the requested word list.
        user_id (int): Identifier of the authenticated user.
        session (AsyncSession): Active database session.

    Returns:
        Notebook: The word list owned by the user.

    Raises:
        HTTPException: If the word list does not exist or belongs to another
            user.
    """
    return await async_get_one_record_by(
        Notebook,
        [Notebook.id == word_list_id, Notebook.user_id == user_id],
        session,
        raise_if_not_found=True,
        not_found_msg="Word list not found",
    )


def _build_saved_word_response(
    vocab: Vocabulary,
    item: NotebookItem,
) -> SavedWordResponse:
    """
    Build a saved-word response without review progress.

    Args:
        vocab (Vocabulary): Vocabulary data shared by all users.
        item (NotebookItem): User-specific saved-word data.

    Returns:
        SavedWordResponse: Combined vocabulary and word-list item response.
    """
    return SavedWordResponse(
        id=vocab.id,
        word=vocab.word,
        word_type=vocab.word_type,
        ipa=vocab.ipa,
        audio_url=vocab.audio_url,
        image_url=vocab.image_url,
        definition_vi=vocab.definition_vi,
        example_sentence=vocab.example_sentence,
        example_translation_vi=vocab.example_translation_vi,
        created_time=item.created_time,
        word_list_item_id=item.id,
        word_list_id=item.notebook_id,
        source_subtitle_id=item.source_subtitle_id,
        context_sentence=item.context_sentence,
        note=item.note,
    )


def _build_saved_word_review_response(
    vocab: Vocabulary,
    progress: PracticeProgress,
    item: NotebookItem,
) -> SavedWordReviewResponse:
    """
    Build a saved-word response containing SRS progress.

    Args:
        vocab (Vocabulary): Vocabulary data shared by all users.
        progress (PracticeProgress): User-specific SRS progress.
        item (NotebookItem): User-specific saved-word data.

    Returns:
        SavedWordReviewResponse: Saved word combined with its SRS state.
    """
    return SavedWordReviewResponse(
        **_build_saved_word_response(vocab, item).model_dump(),
        status=progress.status,
        ease_factor=float(progress.ease_factor),
        repetition_count=progress.repetition_count,
        interval_days=progress.interval_days,
        next_review_at=progress.next_review_at,
        last_reviewed_at=progress.last_reviewed_at,
        personal_note=progress.personal_note,
    )


class WordListService(object):
    """Manage words explicitly saved by a user and their review schedule."""

    @staticmethod
    @transactional()
    async def create_word_list(
        user_id: int,
        data: CreateWordListRequest,
        session: AsyncSession,
    ) -> WordListResponse:
        """Create an empty personal word list."""
        duplicate = await async_get_one_record_by(
            Notebook,
            [Notebook.user_id == user_id, Notebook.name == data.name],
            session,
            raise_if_not_found=False,
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A word list with this name already exists",
            )

        word_list = await async_create_record(
            Notebook,
            {
                "user_id": user_id,
                "name": data.name,
                "description": data.description,
            },
            session,
        )
        return WordListResponse(
            id=word_list.id,
            name=word_list.name,
            description=word_list.description,
            word_count=0,
            created_time=word_list.created_time,
        )

    @staticmethod
    async def get_word_lists(
        user_id: int,
        session: AsyncSession,
    ) -> List[WordListResponse]:
        """List a user's word lists with their saved-word counts."""
        word_count = (
            select(func.count(NotebookItem.id))
            .where(NotebookItem.notebook_id == Notebook.id)
            .correlate(Notebook)
            .scalar_subquery()
        )
        rows = (
            await session.exec(
                select(Notebook, word_count.label("word_count"))
                .where(Notebook.user_id == user_id)
                .order_by(Notebook.created_time.desc())
            )
        ).all()

        return [
            WordListResponse(
                id=word_list.id,
                name=word_list.name,
                description=word_list.description,
                word_count=count,
                created_time=word_list.created_time,
            )
            for word_list, count in rows
        ]

    @staticmethod
    @transactional()
    async def save_word(
        user_id: int,
        word_list_id: int,
        data: SaveWordRequest,
        session: AsyncSession,
    ) -> List[SavedWordResponse]:
        """
        Save every part-of-speech entry for a word to one word list.

        Args:
            user_id (int): Identifier of the authenticated user.
            word_list_id (int): Identifier of the destination word list.
            data (SaveWordRequest): Word, meanings, and optional context data.
            session (AsyncSession): Active database session.

        Returns:
            List[SavedWordResponse]: All entries saved for the word.

        Raises:
            HTTPException: If the word list, subtitle, or dictionary data is
                invalid.
        """
        vocabularies = await _get_or_create_vocabularies(data, session)
        word_list = await _get_user_word_list(word_list_id, user_id, session)

        context_sentence = data.context_sentence
        if data.source_subtitle_id is not None:
            subtitle = await async_get_one_record_by(
                Subtitle,
                [Subtitle.id == data.source_subtitle_id],
                session,
                raise_if_not_found=True,
                not_found_msg="Subtitle not found",
            )
            context_sentence = subtitle.content_en

        responses = []
        for vocab in vocabularies:
            item = await async_get_one_record_by(
                NotebookItem,
                [
                    NotebookItem.notebook_id == word_list.id,
                    NotebookItem.vocabulary_id == vocab.id,
                ],
                session,
                raise_if_not_found=False,
            )
            if not item:
                item = await async_create_record(
                    NotebookItem,
                    {
                        "notebook_id": word_list.id,
                        "vocabulary_id": vocab.id,
                        "source_subtitle_id": data.source_subtitle_id,
                        "context_sentence": context_sentence,
                        "note": data.note,
                    },
                    session,
                )
            elif (
                data.source_subtitle_id is not None
                or data.context_sentence is not None
                or data.note is not None
            ):
                update = {}
                if data.source_subtitle_id is not None:
                    update["source_subtitle_id"] = data.source_subtitle_id
                    update["context_sentence"] = context_sentence
                elif data.context_sentence is not None:
                    update["context_sentence"] = context_sentence
                if data.note is not None:
                    update["note"] = data.note
                item = await async_update_one_record(
                    NotebookItem, item.id, update, session
                )

            progress = await async_get_one_record_by(
                PracticeProgress,
                [
                    PracticeProgress.user_id == user_id,
                    PracticeProgress.vocabulary_id == vocab.id,
                ],
                session,
                raise_if_not_found=False,
            )
            if not progress:
                progress = await async_create_record(
                    PracticeProgress,
                    {"user_id": user_id, "vocabulary_id": vocab.id},
                    session,
                )

            responses.append(_build_saved_word_response(vocab, item))

        return responses

    @staticmethod
    async def get_saved_words(
        user_id: int,
        word_list_id: int,
        filters: SavedWordFilter,
        session: AsyncSession,
    ) -> Tuple[List[SavedWordResponse], int, int]:
        """
        List words explicitly saved in a selected word list.

        Args:
            user_id (int): Identifier of the authenticated user.
            word_list_id (int): Identifier of the selected word list.
            filters (SavedWordFilter): Pagination and keyword filters.
            session (AsyncSession): Active database session.

        Returns:
            Tuple[List[SavedWordResponse], int, int]: Page items, total item
                count, and total page count.

        Raises:
            HTTPException: If the word list is unavailable to the user.
        """
        await _get_user_word_list(word_list_id, user_id, session)

        conditions = [
            NotebookItem.notebook_id == word_list_id,
        ]
        if filters.keyword:
            conditions.append(Vocabulary.word.ilike(f"%{filters.keyword}%"))

        query = (
            select(Vocabulary, NotebookItem)
            .join(NotebookItem, NotebookItem.vocabulary_id == Vocabulary.id)
            .where(*conditions)
            .order_by(NotebookItem.created_time.desc())
        )
        count_query = (
            select(func.count(NotebookItem.id))
            .join(Vocabulary, NotebookItem.vocabulary_id == Vocabulary.id)
            .where(*conditions)
        )
        total = (await session.exec(count_query)).one()

        pages = -(-total // filters.page_size)
        offset, limit = page_size_to_offset_limit(filters.page, filters.page_size)
        query = query.offset(offset).limit(limit)

        rows = (await session.exec(query)).all()
        items = [_build_saved_word_response(vocab, item) for vocab, item in rows]
        return items, total, pages

    @staticmethod
    @transactional()
    async def review_saved_word(
        user_id: int,
        word_list_id: int,
        vocabulary_id: int,
        rating: ReviewRating,
        session: AsyncSession,
        attempt_id: Optional[str] = None,
    ) -> SavedWordReviewResponse:
        """
        Update SRS progress for a word in the selected word list.

        Args:
            user_id (int): Identifier of the authenticated user.
            word_list_id (int): Identifier of the selected word list.
            vocabulary_id (int): Identifier of the reviewed vocabulary entry.
            rating (ReviewRating): User-selected review rating.
            session (AsyncSession): Active database session.

        Returns:
            SavedWordReviewResponse: Saved word with its updated SRS state.

        Raises:
            HTTPException: If the word list or saved vocabulary is not found.
        """
        await _get_user_word_list(word_list_id, user_id, session)

        row = (
            await session.exec(
                select(PracticeProgress, Vocabulary, NotebookItem)
                .join(
                    Vocabulary, 
                    PracticeProgress.vocabulary_id == Vocabulary.id
                )
                .join(
                    NotebookItem,
                    NotebookItem.vocabulary_id == Vocabulary.id,
                )
                .where(
                    PracticeProgress.user_id == user_id,
                    PracticeProgress.vocabulary_id == vocabulary_id,
                    NotebookItem.notebook_id == word_list_id,
                )
            )
        ).first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Word not found in this word list",
            )
        progress, vocab, item = row

        if attempt_id:
            existing = await async_get_one_record_by(
                PracticeAttempt,
                [
                    PracticeAttempt.practice_progress_id == progress.id,
                    PracticeAttempt.attempt_id == attempt_id,
                ],
                session,
                raise_if_not_found=False,
            )
            if existing:
                return _build_saved_word_review_response(vocab, progress, item)

            belongs_elsewhere = (
                await session.exec(
                    select(PracticeAttempt, PracticeProgress)
                    .join(
                        PracticeProgress,
                        PracticeAttempt.practice_progress_id == PracticeProgress.id,
                    )
                    .where(
                        PracticeAttempt.attempt_id == attempt_id,
                        PracticeProgress.user_id == user_id,
                    )
                )
            ).first()
            if belongs_elsewhere and belongs_elsewhere[1].vocabulary_id != vocabulary_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="attempt_id belongs to another vocabulary",
                )

        now = datetime.now(timezone.utc)
        schedule = _calculate_srs_schedule(progress, rating, now)

        progress = await async_update_one_record(
            PracticeProgress,
            progress.id,
            {
                **schedule,
                "last_reviewed_at": now,
            },
            session,
        )
        await async_create_record(
            PracticeAttempt,
            {
                "practice_progress_id": progress.id,
                "attempt_id": attempt_id,
                "rating": rating.value,
                "reviewed_at": now,
            },
            session,
        )

        return _build_saved_word_review_response(vocab, progress, item)

    @staticmethod
    async def get_saved_words_due(
        user_id: int,
        word_list_id: int,
        filters: SavedWordsDueFilter,
        session: AsyncSession,
    ) -> Tuple[List[SavedWordReviewResponse], int, int]:
        """
        Get due words from the selected word list.

        Args:
            user_id (int): Identifier of the authenticated user.
            word_list_id (int): Identifier of the selected word list.
            filters (SavedWordsDueFilter): Pagination parameters.
            session (AsyncSession): Active database session.

        Returns:
            Tuple[List[SavedWordReviewResponse], int, int]: Page items, total
                due count, and total page count.

        Raises:
            HTTPException: If the word list is unavailable to the user.
        """
        await _get_user_word_list(word_list_id, user_id, session)
        now = datetime.now(timezone.utc)

        due_conditions = [
            NotebookItem.notebook_id == word_list_id,
            PracticeProgress.user_id == user_id,
            or_(
                PracticeProgress.next_review_at <= now,
                PracticeProgress.next_review_at.is_(None),
            ),
            PracticeProgress.status != WordStatus.IGNORED.value,
        ]

        total_due = (
            await session.exec(
                select(func.count(NotebookItem.id))
                .join(Vocabulary, NotebookItem.vocabulary_id == Vocabulary.id)
                .join(
                    PracticeProgress,
                    (PracticeProgress.vocabulary_id == Vocabulary.id)
                    & (PracticeProgress.user_id == user_id),
                )
                .where(*due_conditions)
            )
        ).one()

        pages = -(-total_due // filters.page_size)
        offset, limit = page_size_to_offset_limit(filters.page, filters.page_size)
        query = (
            select(Vocabulary, PracticeProgress, NotebookItem)
            .join(NotebookItem, NotebookItem.vocabulary_id == Vocabulary.id)
            .join(
                PracticeProgress,
                (PracticeProgress.vocabulary_id == Vocabulary.id)
                & (PracticeProgress.user_id == user_id),
            )
            .where(*due_conditions)
            .order_by(PracticeProgress.next_review_at.asc().nullsfirst())
            .offset(offset)
            .limit(limit)
        )
        rows = (await session.exec(query)).all()

        items = [
            _build_saved_word_review_response(vocab, progress, item)
            for vocab, progress, item in rows
        ]
        return items, total_due, pages
