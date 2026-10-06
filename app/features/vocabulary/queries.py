from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import async_get_many_records_by, async_get_one_record_by
from app.features.review.model import ReviewProgress
from app.features.vocabulary.model import (
    Vocabulary,
    VocabularyBook,
    VocabularyTopic,
    VocabularyTopicWord,
)


async def get_active_topic(
    book_slug: str,
    topic_slug: str,
    session: AsyncSession,
) -> VocabularyTopic:
    """
    Load a topic only when it belongs to an active vocabulary book.

    Args:
        book_slug (str): The URL slug identifying the active vocabulary book.
        topic_slug (str): The URL slug identifying a topic within the selected book.
        session (AsyncSession): The database session used for record operations.

    Returns:
        VocabularyTopic: The matching topic belonging to an active vocabulary book.

    Raises:
        HTTPException: If the topic does not belong to the selected active book or does
            not exist.
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


async def get_topic_words_with_progress(
    topic_id: int,
    user_id: int,
    session: AsyncSession,
) -> list[tuple[Vocabulary, VocabularyTopicWord, Optional[ReviewProgress]]]:
    """
    Load topic words and attach the user's optional review progress.

    Args:
        topic_id (int): The ID of the vocabulary topic.
        user_id (int): The ID of the user.
        session (AsyncSession): The database session.

    Returns:
        list[tuple[Vocabulary, VocabularyTopicWord, Optional[ReviewProgress]]]:
    """
    topic_words = await async_get_many_records_by(
        VocabularyTopicWord,
        [VocabularyTopicWord.topic_id == topic_id],
        session,
        options=[joinedload(VocabularyTopicWord.vocabulary, innerjoin=True)],
        raise_if_not_found=False,
    )
    if not topic_words:
        return []

    vocabulary_ids = [topic_word.vocabulary_id for topic_word in topic_words]
    progress_rows = await async_get_many_records_by(
        ReviewProgress,
        [
            ReviewProgress.user_id == user_id,
            ReviewProgress.vocabulary_id.in_(vocabulary_ids),
        ],
        session,
        raise_if_not_found=False,
    )
    progress_by_vocabulary_id = {
        progress.vocabulary_id: progress for progress in progress_rows
    }
    return [
        (
            topic_word.vocabulary,
            topic_word,
            progress_by_vocabulary_id.get(topic_word.vocabulary_id),
        )
        for topic_word in topic_words
    ]
