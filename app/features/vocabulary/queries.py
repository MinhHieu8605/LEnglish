from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.features.review.model import ReviewProgress
from app.features.vocabulary.model import Vocabulary, VocabularyTopicWord


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
    rows = (
        await session.exec(
            select(Vocabulary, VocabularyTopicWord)
            .join(
                VocabularyTopicWord,
                VocabularyTopicWord.vocabulary_id == Vocabulary.id,
            )
            .where(VocabularyTopicWord.topic_id == topic_id)
        )
    ).all()
    if not rows:
        return []

    vocabulary_ids = [vocab.id for vocab, _ in rows]
    progress_rows = (
        await session.exec(
            select(ReviewProgress).where(
                ReviewProgress.user_id == user_id,
                ReviewProgress.vocabulary_id.in_(vocabulary_ids),
            )
        )
    ).all()
    progress_by_vocabulary_id = {
        progress.vocabulary_id: progress for progress in progress_rows
    }
    return [
        (vocab, topic_word, progress_by_vocabulary_id.get(vocab.id))
        for vocab, topic_word in rows
    ]
