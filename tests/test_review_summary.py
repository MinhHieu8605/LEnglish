import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql

from app.features.preferences.schemas import UserPreferencesResponse
from app.features.review.model import ReviewAttempt, ReviewProgress
from app.features.review.service import ReviewService
from app.main import app  # Load all models referenced by the table foreign keys.


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 1, 17, 30, tzinfo=timezone.utc).astimezone(tz)


@pytest.mark.parametrize("daily_target", [1, 5])
def test_review_summary_counts_first_reviews_in_user_timezone(monkeypatch, daily_target):
    monkeypatch.setattr("app.features.review.service.datetime", FixedDateTime)
    monkeypatch.setattr(
        "app.features.review.service.UserPreferencesService.get_preferences",
        AsyncMock(return_value=UserPreferencesResponse(user_id=7, daily_new_words=daily_target)),
    )
    # Midnight on October 2 in Ho Chi Minh City is 17:00 UTC on October 1.
    day_start = datetime(2026, 10, 1, 17, tzinfo=timezone.utc)
    engine = create_engine("sqlite://")
    try:
        ReviewProgress.__table__.create(engine)
        ReviewAttempt.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(ReviewProgress.__table__.insert(), [
                {"id": 1, "user_id": 7, "vocabulary_id": 1, "status": "learning", "next_review_at": None},
                {"id": 2, "user_id": 7, "vocabulary_id": 2, "status": "review", "next_review_at": day_start + timedelta(days=2)},
                {"id": 3, "user_id": 7, "vocabulary_id": 3, "status": "new", "next_review_at": None},
                {"id": 4, "user_id": 8, "vocabulary_id": 4, "status": "learning", "next_review_at": None},
                {"id": 5, "user_id": 7, "vocabulary_id": 5, "status": "learning", "next_review_at": day_start},
                {"id": 6, "user_id": 7, "vocabulary_id": 6, "status": "ignored", "next_review_at": day_start},
                {"id": 7, "user_id": 7, "vocabulary_id": 7, "status": "review", "next_review_at": day_start + timedelta(days=2)},
            ])
            connection.execute(ReviewAttempt.__table__.insert(), [
                {"review_progress_id": progress_id, "rating": "good", "reviewed_at": reviewed_at}
                for progress_id, reviewed_at in [
                    (1, day_start), (1, day_start + timedelta(minutes=10)),
                    (2, day_start - timedelta(seconds=1)), (2, day_start + timedelta(minutes=10)),
                    (4, day_start + timedelta(minutes=10)),
                    (5, day_start + timedelta(minutes=10)),
                    (7, day_start + timedelta(days=1)),
                ]
            ])

            class Session:
                async def exec(self, statement):
                    statement.compile(dialect=postgresql.dialect())
                    return connection.execute(statement).scalars()

            summary = asyncio.run(ReviewService.get_review_summary(7, Session()))

        assert summary.due_word_count == 2
        assert summary.daily_new_word_target == daily_target
        assert summary.new_words_learned_today == 2
        assert summary.remaining_new_words == max(0, daily_target - 2)
    finally:
        engine.dispose()
