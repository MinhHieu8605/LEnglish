from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import async_get_many_records_by, async_get_one_record_by
from app.features.vocabulary.model import (
    Vocabulary,
    VocabularyBook,
    VocabularyProgress,
    VocabularyTopic,
    VocabularyTopicWord,
)
from app.features.vocabulary.schemas import (
    TopicWordResponse,
    VocabularyTopicResponse,
)
from app.utils.constants import WordStatus


def _build_topic_response(
    topic: VocabularyTopic,
    word_count: int,
    mastered_count: int,
    learning_count: int,
    new_count: int,
) -> VocabularyTopicResponse:
    """Build a topic response with the user's aggregated progress."""
    return VocabularyTopicResponse(
        id=topic.id,
        book_id=topic.book_id,
        name=topic.name,
        slug=topic.slug,
        order_num=topic.order_num,
        word_count=word_count,
        mastered_word=mastered_count,
        learning_word=learning_count,
        new_word=new_count,
    )


def _build_topic_word_response(
    vocab: Vocabulary,
    order_num: int,
    progress: Optional[VocabularyProgress] = None,
) -> TopicWordResponse:
    """Build a curated-topic word with optional user progress."""
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


class VocabularyService(object):
    """Read curated vocabulary collections and user progress within them."""

    @staticmethod
    async def get_books(session: AsyncSession) -> List[VocabularyBook]:
        """Fetch all active vocabulary books sorted by creation date."""
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
        """Fetch topics for a collection with aggregated user progress."""
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
                                | (
                                    VocabularyProgress.status
                                    == WordStatus.REVIEW.value
                                ),
                                1,
                            )
                        )
                    ).label("learning_count"),
                    func.count(
                        case(
                            (
                                VocabularyTopicWord.id.is_not(None)
                                & (
                                    VocabularyProgress.id.is_(None)
                                    | (
                                        VocabularyProgress.status
                                        == WordStatus.NEW.value
                                    )
                                ),
                                1,
                            )
                        )
                    ).label("new_count"),
                )
                .where(VocabularyTopic.book_id == book.id)
                .join(
                    VocabularyTopicWord,
                    VocabularyTopic.id == VocabularyTopicWord.topic_id,
                    isouter=True,
                )
                .join(
                    VocabularyProgress,
                    (
                        VocabularyProgress.vocabulary_id
                        == VocabularyTopicWord.vocabulary_id
                    )
                    & (VocabularyProgress.user_id == user_id),
                    isouter=True,
                )
                .group_by(VocabularyTopic.id)
                .order_by(VocabularyTopic.order_num.asc())
            )
        ).all()

        return [
            _build_topic_response(
                topic,
                word_count,
                mastered_count,
                learning_count,
                new_count,
            )
            for (
                topic,
                word_count,
                mastered_count,
                learning_count,
                new_count,
            ) in rows
        ]

    @staticmethod
    async def get_topic_words(
        user_id: int, topic_slug: str, session: AsyncSession
    ) -> List[TopicWordResponse]:
        """Fetch words in a curated topic with optional user progress."""
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
                .join(
                    VocabularyTopicWord,
                    VocabularyTopicWord.vocabulary_id == Vocabulary.id,
                )
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
