from typing import List, Optional

from sqlalchemy import case, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import async_get_many_records_by, async_get_one_record_by
from app.features.review.model import ReviewProgress
from app.features.vocabulary.model import (
    Vocabulary,
    VocabularyBook,
    VocabularyTopic,
    VocabularyTopicWord,
)
from app.features.vocabulary.queries import (
    get_active_topic,
    get_topic_words_with_progress,
)
from app.features.vocabulary.schemas import TopicWordResponse, VocabularyTopicResponse
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
        mastered_word_count=mastered_count,
        learning_word_count=learning_count,
        new_word_count=new_count,
    )


def _build_topic_word_response(
    vocab: Vocabulary,
    order_num: int,
    progress: Optional[ReviewProgress] = None,
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
    async def list_books(session: AsyncSession) -> List[VocabularyBook]:
        """Fetch all active vocabulary books sorted by creation date."""
        return await async_get_many_records_by(
            VocabularyBook,
            [VocabularyBook.deleted.is_(False)],
            session,
            order_by=[VocabularyBook.created_time.asc()],
            raise_if_not_found=False,
        )

    @staticmethod
    async def list_topics(
        user_id: int, book_slug: str, session: AsyncSession
    ) -> List[VocabularyTopicResponse]:
        """
        Fetch topics for a collection with aggregated user progress.

        Args:
            user_id (int): The ID of the user.
            book_slug (str): The slug of the vocabulary book.
            session (AsyncSession): The database session.

        Returns:
            List[VocabularyTopicResponse]: A list of topics with user progress.
        """
        book = await async_get_one_record_by(
            VocabularyBook,
            [VocabularyBook.slug == book_slug, VocabularyBook.deleted.is_(False)],
            session,
            raise_if_not_found=True,
            not_found_msg="Vocabulary book not found",
        )

        mastered = ReviewProgress.status == WordStatus.MASTERED.value
        learning = ReviewProgress.status.in_(
            [WordStatus.LEARNING.value, WordStatus.REVIEW.value]
        )
        is_new = VocabularyTopicWord.id.is_not(None) & (
            ReviewProgress.id.is_(None)
            | (ReviewProgress.status == WordStatus.NEW.value)
        )
        rows = (
            await session.exec(
                select(
                    VocabularyTopic,
                    func.count(VocabularyTopicWord.id).label("word_count"),
                    func.count(case((mastered, 1))).label("mastered_count"),
                    func.count(case((learning, 1))).label("learning_count"),
                    func.count(case((is_new, 1))).label("new_count"),
                )
                .where(VocabularyTopic.book_id == book.id)
                .join(
                    VocabularyTopicWord,
                    VocabularyTopic.id == VocabularyTopicWord.topic_id,
                )
                .join(
                    ReviewProgress,
                    (ReviewProgress.vocabulary_id == VocabularyTopicWord.vocabulary_id)
                    & (ReviewProgress.user_id == user_id),
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
    async def list_words(
        user_id: int,
        topic_slug: str,
        session: AsyncSession,
        book_slug: str | None = None,
    ) -> List[TopicWordResponse]:
        """
        Fetch words in a curated topic with optional user progress.

        Args:
            user_id (int): The ID of the user.
            topic_slug (str): The slug of the vocabulary topic.
            session (AsyncSession): The database session.
            book_slug (str | None): Optional slug of the vocabulary book to filter by.

        Returns:
            List[TopicWordResponse]: A list of words in the topic with user progress.
        """
        if book_slug:
            topic = await get_active_topic(book_slug, topic_slug, session)
        else:
            topic = await async_get_one_record_by(
                VocabularyTopic,
                [
                    VocabularyTopic.slug == topic_slug,
                    VocabularyTopic.book.has(VocabularyBook.deleted.is_(False)),
                ],
                session,
                not_found_msg="Vocabulary topic not found",
                raise_if_not_found=True,
            )

        rows = await get_topic_words_with_progress(topic.id, user_id, session)
        rows.sort(key=lambda row: row[1].order_num)

        return [
            _build_topic_word_response(vocab, topic_word.order_num, progress)
            for vocab, topic_word, progress in rows
        ]
