"""Pure spaced-repetition calculations used by vocabulary review flows."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil
from typing import Dict

from app.utils.constants import ReviewRating, WordStatus

_SRS_INTERVAL_STEPS = [1, 3, 5, 8, 15, 21]
_MIN_EASE_FACTOR = 1.30
_MAX_INTERVAL_DAYS = 365
_AGAIN_DELAY = timedelta(minutes=10)
_HARD_DELAY = timedelta(hours=12)


@dataclass(frozen=True)
class ReviewProgressState:
    """
    The SRS fields required to calculate a review schedule.

    Attributes:
        repetition_count (int): The number of successful repetitions in the current
            review state.
        interval_days (int): The scheduled review interval in whole days.
        ease_factor (float): The multiplier used to calculate future successful-review
            intervals.
    """

    repetition_count: int = 0
    interval_days: int = 0
    ease_factor: float = 2.50


@dataclass(frozen=True)
class ReviewSchedule:
    """
    The next SRS state for one rating.

    Attributes:
        repetition_count (int): The number of successful repetitions in the current
            review state.
        interval_days (int): The scheduled review interval in whole days.
        ease_factor (float): The multiplier used to calculate future successful-review
            intervals.
        next_review_at (datetime): The timestamp when the next review becomes due.
        status (str): The current learning or session state.
        _reviewed_at (datetime): The reference timestamp used to calculate sub-day
            review intervals.
    """

    repetition_count: int
    interval_days: int
    ease_factor: float
    next_review_at: datetime
    status: str
    _reviewed_at: datetime = datetime.min

    @property
    def interval_seconds(self) -> int:
        """
        Return the scheduled delay from the review timestamp in seconds.

        Returns:
            int: The scheduled delay in seconds, including intervals shorter than one
                day.
        """
        if self.interval_days:
            return int(self.interval_days * 86400)
        return int((self.next_review_at - self._reviewed_at).total_seconds())


def _next_good_interval(
    repetition_count: int, current_interval: int, ease_factor: float
) -> int:
    """
    Calculate the next interval for a successful review.

    Args:
        repetition_count (int): The updated successful-review count, starting at one.
        current_interval (int): The previous successful-review interval in days.
        ease_factor (float): The multiplier used to extend the successful-review
            interval.

    Returns:
        int: The next successful-review interval in days, capped at the configured
            maximum.
    """
    if repetition_count <= len(_SRS_INTERVAL_STEPS):
        return _SRS_INTERVAL_STEPS[repetition_count - 1]
    interval = ceil(max(current_interval, _SRS_INTERVAL_STEPS[-1]) * ease_factor)
    return min(interval, _MAX_INTERVAL_DAYS)


def _status_for_interval(interval_days: int) -> str:
    """
    Map an interval length to the corresponding vocabulary status.

    Args:
        interval_days (int): The scheduled review interval in whole days.

    Returns:
        str: The learning, review, or mastered status corresponding to the interval.
    """
    if interval_days >= _SRS_INTERVAL_STEPS[-1]:
        return WordStatus.MASTERED.value
    if interval_days >= 1:
        return WordStatus.REVIEW.value
    return WordStatus.LEARNING.value


def calculate_review_schedule(
    progress: ReviewProgressState,
    rating: ReviewRating,
    reviewed_at: datetime,
) -> ReviewSchedule:
    """
    Calculate the next SRS schedule without truncating the review time.

    Args:
        progress (ReviewProgressState): Current SRS state.
        rating (ReviewRating): User-selected review rating.
        reviewed_at (datetime): Timestamp at which the review was submitted.

    Returns:
        ReviewSchedule: The next progress state and review timestamp.
    """
    repetition_count = int(progress.repetition_count)
    current_interval = int(progress.interval_days)
    ease_factor = float(progress.ease_factor)

    if rating == ReviewRating.AGAIN:
        return ReviewSchedule(
            repetition_count=0,
            interval_days=0,
            ease_factor=max(_MIN_EASE_FACTOR, round(ease_factor - 0.20, 2)),
            next_review_at=reviewed_at + _AGAIN_DELAY,
            status=WordStatus.LEARNING.value,
            _reviewed_at=reviewed_at,
        )

    if rating == ReviewRating.HARD:
        ease_factor = max(_MIN_EASE_FACTOR, round(ease_factor - 0.15, 2))
        if current_interval <= 1:
            return ReviewSchedule(
                repetition_count=repetition_count,
                interval_days=0,
                ease_factor=ease_factor,
                next_review_at=reviewed_at + _HARD_DELAY,
                status=WordStatus.LEARNING.value,
                _reviewed_at=reviewed_at,
            )
        interval_days = min(
            max(current_interval + 1, ceil(current_interval * 1.20)),
            _MAX_INTERVAL_DAYS,
        )
    else:
        repetition_count += 1
        interval_days = _next_good_interval(
            repetition_count, current_interval, ease_factor
        )
        if rating == ReviewRating.EASY:
            ease_factor = round(ease_factor + 0.15, 2)
            if repetition_count > 1:
                interval_days = min(
                    max(interval_days + 1, ceil(interval_days * 1.30)),
                    _MAX_INTERVAL_DAYS,
                )

    return ReviewSchedule(
        repetition_count=repetition_count,
        interval_days=interval_days,
        ease_factor=ease_factor,
        next_review_at=reviewed_at + timedelta(days=interval_days),
        status=_status_for_interval(interval_days),
        _reviewed_at=reviewed_at,
    )


def build_review_options(
    progress: ReviewProgressState, reviewed_at: datetime
) -> Dict[ReviewRating, ReviewSchedule]:
    """
    Calculate the schedule for every supported review rating.

    Args:
        progress (ReviewProgressState): Current SRS state.
        reviewed_at (datetime): Timestamp used as the schedule base.

    Returns:
        Dict[ReviewRating, ReviewSchedule]: One schedule per rating.
    """
    return {
        rating: calculate_review_schedule(progress, rating, reviewed_at)
        for rating in ReviewRating
    }


def classify_progress(
    status: str | None,
    next_review_at: datetime | None,
    now: datetime,
) -> str:
    """
    Classify persisted progress for review-queue filtering and ordering.

    Args:
        status (str | None): The persisted vocabulary learning status, if available.
        next_review_at (datetime | None): The scheduled next review timestamp, if
            available.
        now (datetime): The current timestamp used to exclude future activity or
            classify review progress.

    Returns:
        str: One of new, ignored, due, overdue, or future for queue filtering.
    """
    if not status or status == WordStatus.NEW.value:
        return "new"
    if status == WordStatus.IGNORED.value:
        return "ignored"
    if not next_review_at:
        return "due" if status == WordStatus.LEARNING.value else "future"

    compare_now = now
    if next_review_at.tzinfo is None and now.tzinfo is not None:
        compare_now = now.replace(tzinfo=None)

    if next_review_at < compare_now:
        return "overdue"
    if next_review_at == compare_now:
        return "due"
    return "future"
