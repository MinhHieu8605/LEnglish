import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import raiseload
from sqlmodel import Session, create_engine

from app.features.review.model import ReviewAttempt, ReviewProgress
from app.features.review.schemas import ReviewWordRequest
from app.features.review.service import ReviewService
from app.features.vocabulary.model import Vocabulary, VocabularyTopicWord
from app.features.vocabulary.queries import get_topic_words_with_progress
from app.main import app  # Load all models referenced by the table foreign keys.
from app.utils.constants import ReviewRating


@pytest.fixture
def query_session():
    engine = create_engine("sqlite://")
    reviewed_at = datetime(2026, 10, 4, tzinfo=timezone.utc)
    try:
        for model in (Vocabulary, VocabularyTopicWord, ReviewProgress, ReviewAttempt):
            model.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(Vocabulary.__table__.insert(), [
                {"id": 1, "word": "apple"},
                {"id": 2, "word": "book"},
                {"id": 3, "word": "cat"},
            ])
            connection.execute(VocabularyTopicWord.__table__.insert(), [
                {"topic_id": 10, "vocabulary_id": 1, "order_num": 1},
                {"topic_id": 10, "vocabulary_id": 2, "order_num": 2},
                {"topic_id": 20, "vocabulary_id": 3, "order_num": 1},
            ])
            connection.execute(ReviewProgress.__table__.insert(), [
                {"id": 1, "user_id": 7, "vocabulary_id": 1, "status": "review",
                 "next_review_at": reviewed_at + timedelta(days=1)},
                {"id": 2, "user_id": 8, "vocabulary_id": 2, "status": "learning",
                 "next_review_at": reviewed_at + timedelta(days=1)},
            ])
            connection.execute(ReviewAttempt.__table__.insert(), {
                "review_progress_id": 1, "attempt_id": "existing-attempt",
                "rating": "good", "reviewed_at": reviewed_at,
            })

        with Session(engine) as sync_session:
            class QuerySession:
                query_count = 0

                async def exec(self, statement):
                    statement.compile(dialect=postgresql.dialect())
                    self.query_count += 1
                    # Fail if relationships are accessed without eager loading.
                    return sync_session.exec(statement.options(raiseload("*")))

            yield QuerySession()
    finally:
        engine.dispose()


def test_topic_words_keep_user_progress_optional(query_session):
    rows = asyncio.run(get_topic_words_with_progress(10, 7, query_session))

    by_vocabulary_id = {vocab.id: (vocab, item, progress) for vocab, item, progress in rows}
    assert set(by_vocabulary_id) == {1, 2}
    assert by_vocabulary_id[1][0].word == "apple"
    assert by_vocabulary_id[1][1].topic_id == 10
    assert by_vocabulary_id[1][2].user_id == 7
    assert by_vocabulary_id[2][2] is None
    assert query_session.query_count == 2


def test_empty_topic_returns_no_words(query_session):
    assert asyncio.run(get_topic_words_with_progress(99, 7, query_session)) == []
    assert query_session.query_count == 1


def test_topic_without_user_progress_still_returns_words(query_session):
    rows = asyncio.run(get_topic_words_with_progress(10, 9, query_session))

    assert len(rows) == 2
    assert all(progress is None for _, _, progress in rows)
    assert query_session.query_count == 2


def test_repeated_attempt_returns_stored_review(query_session):
    data = ReviewWordRequest(attempt_id="existing-attempt", rating=ReviewRating.AGAIN)
    result = asyncio.run(ReviewService._review_word(7, 1, data, query_session))

    assert result.attempt_id == "existing-attempt"
    assert result.vocabulary_id == 1
    assert result.rating == ReviewRating.GOOD
    assert result.status == "review"
    assert query_session.query_count == 1


@pytest.mark.parametrize(("user_id", "vocabulary_id"), [(8, 1), (7, 2)])
def test_attempt_for_another_review_is_rejected(query_session, user_id, vocabulary_id):
    data = ReviewWordRequest(attempt_id="existing-attempt", rating=ReviewRating.GOOD)

    with pytest.raises(HTTPException) as error:
        asyncio.run(ReviewService._review_word(user_id, vocabulary_id, data, query_session))

    assert error.value.status_code == 409
    assert query_session.query_count == 1


def test_missing_attempt_continues_to_vocabulary_lookup(query_session):
    data = ReviewWordRequest(attempt_id="new-attempt", rating=ReviewRating.GOOD)

    with pytest.raises(HTTPException) as error:
        asyncio.run(ReviewService._review_word(7, 99, data, query_session))

    assert error.value.status_code == 404
    assert error.value.detail == "Vocabulary word not found"
    assert query_session.query_count == 2
