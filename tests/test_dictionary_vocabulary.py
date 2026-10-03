from datetime import datetime, timedelta, timezone

from app.features.review.srs import ReviewProgressState, calculate_review_schedule
from app.features.wordlist.schemas import SaveWordRequest
from app.utils.constants import ReviewRating, WordStatus


def test_save_word_request_normalizes_input():
    request = SaveWordRequest(word="  take off  ", translation_vi="  cởi ra  ")

    assert request.word == "take off"
    assert request.translation_vi == "cởi ra"


def test_review_schedule_again_repeats_in_ten_minutes():
    reviewed_at = datetime(2026, 9, 21, 9, tzinfo=timezone.utc)
    schedule = calculate_review_schedule(
        ReviewProgressState(repetition_count=3, interval_days=8, ease_factor=2.5),
        ReviewRating.AGAIN,
        reviewed_at,
    )

    assert schedule.status == WordStatus.LEARNING.value
    assert schedule.repetition_count == 0
    assert schedule.next_review_at == reviewed_at + timedelta(minutes=10)
