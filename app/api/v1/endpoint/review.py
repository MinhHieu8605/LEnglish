from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.review.schemas import (
    ReviewTopicClozeRequest,
    ReviewClozeResponse,
    ReviewTopicCheckRequest,
    ReviewCheckResponse,
    ReviewQueueResponse,
    ReviewSessionAttemptRequest,
    ReviewSessionResponse,
    ReviewTopicSessionStartRequest,
    ReviewSummaryResponse,
    ReviewWordRequest,
    ReviewWordSubmitRequest,
    ReviewWordResponse,
)
from app.features.review.service import ReviewService
from app.features.wordlist.schemas import (
    SavedWordListMeta,
    SavedWordReviewResponse,
    SavedWordsDueFilter,
    SavedWordsDueResponse,
)
from app.features.wordlist.service import WordListService
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
    "/queue",
    response_model=ReviewQueueResponse | SavedWordsDueResponse,
)
async def get_review_queue(
    request: Request,
    book_slug: str | None = Query(default=None, min_length=1),
    topic_slug: str | None = Query(default=None, min_length=1),
    word_list_id: int | None = Query(default=None, ge=1),
    status: Literal["due"] | None = None,
    mode: ReviewMode = ReviewMode.FLASHCARD,
    scope: ReviewScope = ReviewScope.DUE,
    filters: SavedWordsDueFilter = Depends(),
    session: AsyncSession = Depends(get_session),
) -> ReviewQueueResponse | SavedWordsDueResponse:
    """Return a topic queue or a paginated saved-word due queue."""
    user_id = get_user_id_from_request(request)
    if word_list_id is not None:
        if book_slug is not None or topic_slug is not None or scope != ReviewScope.DUE:
            raise HTTPException(422, "Choose either a topic queue or a saved-word due queue")
        items, total, pages = await WordListService.list_due_words(
            user_id, word_list_id, filters, session
        )
        return SavedWordsDueResponse(
            data=items,
            metadata=SavedWordListMeta(
                total=total, page=filters.page, page_size=filters.page_size, pages=pages
            ),
        )
    if book_slug is None or topic_slug is None:
        raise HTTPException(422, "book_slug and topic_slug are required for a topic queue")
    if status is not None and scope != ReviewScope.DUE:
        raise HTTPException(422, "status=due requires scope=due")
    return await ReviewService.get_review_queue(
        user_id, book_slug, topic_slug, mode, scope, session
    )


@router.post(
    "/words/{vocabulary_id}/check",
    response_model=ReviewCheckResponse
)
async def check_review_answer(
    request: Request,
    vocabulary_id: int,
    data: ReviewTopicCheckRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewCheckResponse:
    """Check a typing answer for a word in the requested topic."""
    await ReviewService.ensure_topic_vocabulary(
        data.book_slug, data.topic_slug, vocabulary_id, session
    )
    user_id = get_user_id_from_request(request)
    return await ReviewService.check_answer(user_id, vocabulary_id, data, session)


@router.post(
    "/words/{vocabulary_id}/cloze",
    response_model=ReviewClozeResponse,
)
async def get_review_cloze(
    request: Request,
    vocabulary_id: int,
    data: ReviewTopicClozeRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewClozeResponse:
    """Return a cloze exercise for one vocabulary word."""
    await ReviewService.ensure_topic_vocabulary(
        data.book_slug, data.topic_slug, vocabulary_id, session
    )
    user_id = get_user_id_from_request(request)
    return await ReviewService.generate_cloze(
        user_id, vocabulary_id, data.attempt_id, session
    )


@router.post(
    "/words/{vocabulary_id}",
    response_model=ReviewWordResponse | SavedWordReviewResponse,
)
async def review_word(
    request: Request,
    vocabulary_id: int,
    data: ReviewWordSubmitRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewWordResponse | SavedWordReviewResponse:
    """Record a review rating for a vocabulary entry."""
    user_id = get_user_id_from_request(request)
    if data.word_list_id is not None:
        return await WordListService.record_review(
            user_id, data.word_list_id, vocabulary_id, data.rating, session, data.attempt_id
        )
    review_data = ReviewWordRequest(**data.model_dump(exclude={"word_list_id"}))
    return await ReviewService.record_review(user_id, vocabulary_id, review_data, session)


@router.post(
    "/sessions",
    response_model=ReviewSessionResponse,
    status_code=201,
)
async def create_review_session(
    request: Request,
    data: ReviewTopicSessionStartRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewSessionResponse:
    """Create a review session for a vocabulary topic."""
    user_id = get_user_id_from_request(request)
    return await ReviewService.start_review_session(
        user_id, data.book_slug, data.topic_slug, data, session
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
