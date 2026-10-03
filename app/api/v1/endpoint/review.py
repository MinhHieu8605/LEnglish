from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.review.schemas import (
    ReviewClozeRequest,
    ReviewClozeResponse,
    ReviewCheckRequest,
    ReviewCheckResponse,
    ReviewQueueResponse,
    ReviewSessionAttemptRequest,
    ReviewSessionResponse,
    ReviewSessionStartRequest,
    ReviewSummaryResponse,
    ReviewWordRequest,
    ReviewWordResponse,
)
from app.features.review.service import ReviewService
from app.utils.common import get_user_id_from_request
from app.utils.constants import ReviewScope, ReviewMode

router = APIRouter()


@router.get("/today", response_model=ReviewSummaryResponse)
async def get_review_summary(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ReviewSummaryResponse:
    """Return due vocabulary and today's new-word goal for the current user."""
    user_id = get_user_id_from_request(request)
    return await ReviewService.get_review_summary(user_id, session)


@router.get(
    "/books/{book_slug}/topics/{topic_slug}/queue", 
    response_model=ReviewQueueResponse
)
async def get_review_queue(
    request: Request,
    book_slug: str,
    topic_slug: str,
    mode: ReviewMode = ReviewMode.FLASHCARD,
    scope: ReviewScope = ReviewScope.DUE,
    session: AsyncSession = Depends(get_session),
) -> ReviewQueueResponse:
    """Return the review queue for a vocabulary topic."""
    user_id = get_user_id_from_request(request)
    return await ReviewService.get_review_queue(
        user_id, book_slug, topic_slug, mode, scope, session
    )


@router.post(
    "/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/check", 
    response_model=ReviewCheckResponse
)
async def check_review_answer(
    request: Request,
    book_slug: str,
    topic_slug: str,
    vocabulary_id: int,
    data: ReviewCheckRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewCheckResponse:
    """Check a typing answer for a word in the requested topic."""
    await ReviewService.ensure_topic_vocabulary(
        book_slug, topic_slug, vocabulary_id, session
    )
    user_id = get_user_id_from_request(request)
    return await ReviewService.check_answer(user_id, vocabulary_id, data, session)


@router.post(
    "/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/cloze",
    response_model=ReviewClozeResponse,
)
async def get_review_cloze(
    request: Request,
    book_slug: str,
    topic_slug: str,
    vocabulary_id: int,
    data: ReviewClozeRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewClozeResponse:
    """Return a cloze exercise for one vocabulary word."""
    await ReviewService.ensure_topic_vocabulary(
        book_slug, topic_slug, vocabulary_id, session
    )
    user_id = get_user_id_from_request(request)
    return await ReviewService.generate_cloze(
        user_id, vocabulary_id, data.attempt_id, session
    )


@router.post("/words/{vocabulary_id}", response_model=ReviewWordResponse)
async def review_word(
    request: Request,
    vocabulary_id: int,
    data: ReviewWordRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewWordResponse:
    """Record a review rating for a vocabulary entry."""
    user_id = get_user_id_from_request(request)
    return await ReviewService.record_review(user_id, vocabulary_id, data, session)


@router.post(
    "/books/{book_slug}/topics/{topic_slug}/sessions",
    response_model=ReviewSessionResponse,
    status_code=201,
)
async def create_review_session(
    request: Request,
    book_slug: str,
    topic_slug: str,
    data: ReviewSessionStartRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewSessionResponse:
    """Create a review session for a vocabulary topic."""
    user_id = get_user_id_from_request(request)
    return await ReviewService.start_review_session(
        user_id, book_slug, topic_slug, data, session
    )


@router.get("/sessions/{session_id}", response_model=ReviewSessionResponse)
async def get_review_session(
    request: Request,
    session_id: int,
    session: AsyncSession = Depends(get_session),
) -> ReviewSessionResponse:
    """Return one review session owned by the current user."""
    user_id = get_user_id_from_request(request)
    return await ReviewService.get_review_session(user_id, session_id, session)


@router.post("/sessions/{session_id}/attempts", response_model=ReviewSessionResponse)
async def record_review_attempt(
    request: Request,
    session_id: int,
    data: ReviewSessionAttemptRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewSessionResponse:
    """Record one answer in a review session."""
    user_id = get_user_id_from_request(request)
    return await ReviewService.record_review_attempt(
        user_id, session_id, data, session
    )


@router.post("/sessions/{session_id}/complete", response_model=ReviewSessionResponse)
async def complete_review_session(
    request: Request,
    session_id: int,
    session: AsyncSession = Depends(get_session),
) -> ReviewSessionResponse:
    """Mark a review session as completed."""
    user_id = get_user_id_from_request(request)
    return await ReviewService.complete_review_session(user_id, session_id, session)
