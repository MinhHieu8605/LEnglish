from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.practice import service
from app.features.practice.schemas import (
    ClozePracticeRequest,
    ClozePracticeResponse,
    PracticeCheckRequest,
    PracticeCheckResponse,
    PracticeDeckResponse,
    PracticeSessionResponse,
    PracticeSessionAttemptRequest,
    PracticeSessionStartRequest,
    VocabularyReviewRequest,
    VocabularyReviewResponse,
)
from app.utils.common import get_user_id_from_request
from app.utils.constants import PracticeScope, VocabularyDeckMode

router = APIRouter()


@router.get(
    "/books/{book_slug}/topics/{topic_slug}/practice", 
    response_model=PracticeDeckResponse
)
async def get_practice_deck(
    request: Request,
    book_slug: str,
    topic_slug: str,
    mode: VocabularyDeckMode = VocabularyDeckMode.FLASHCARD,
    scope: PracticeScope = PracticeScope.DUE,
    session: AsyncSession = Depends(get_session),
):
    """
    Return the practice deck for a vocabulary topic.

    Args:
        request (Request): The HTTP request object.
        book_slug (str): The slug of the book.
        topic_slug (str): The slug of the topic.
        mode (VocabularyDeckMode): The mode of the practice deck (default is FLASHCARD).
        scope (PracticeScope): The scope of the practice deck (default is DUE).
        session (AsyncSession): The database session.

    Returns:
        PracticeDeckResponse: The practice deck response containing the vocabulary entries.
    """
    user_id = get_user_id_from_request(request)
    return await service.get_deck(user_id, book_slug, topic_slug, mode, scope, session)


@router.post(
    "/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/practice/check", 
    response_model=PracticeCheckResponse
)
async def check_practice_answer(
    request: Request,
    book_slug: str,
    topic_slug: str,
    vocabulary_id: int,
    data: PracticeCheckRequest,
    session: AsyncSession = Depends(get_session),
):
    """Check a typing answer for a word in the requested topic."""
    await service.ensure_topic_vocabulary(
        book_slug, topic_slug, vocabulary_id, session
    )
    user_id = get_user_id_from_request(request)
    return await service.check_typing(user_id, vocabulary_id, data, session)


@router.post("/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/practice/cloze", response_model=ClozePracticeResponse)
async def get_cloze_practice(
    request: Request,
    book_slug: str,
    topic_slug: str,
    vocabulary_id: int,
    data: ClozePracticeRequest,
    session: AsyncSession = Depends(get_session),
):
    """Generate a cloze exercise for a word in the requested topic."""
    await service.ensure_topic_vocabulary(
        book_slug, topic_slug, vocabulary_id, session
    )
    user_id = get_user_id_from_request(request)
    return await service.generate_cloze(user_id, vocabulary_id, data.attempt_id, session)


@router.post("/words/{vocabulary_id}/review", response_model=VocabularyReviewResponse)
async def review_vocabulary(
    request: Request,
    vocabulary_id: int,
    data: VocabularyReviewRequest,
    session: AsyncSession = Depends(get_session),
):
    """Record a review rating for a vocabulary entry."""
    user_id = get_user_id_from_request(request)
    return await service.review_vocabulary(user_id, vocabulary_id, data, session)


@router.post("/books/{book_slug}/topics/{topic_slug}/practice-sessions", response_model=PracticeSessionResponse, status_code=201)
async def create_practice_session(
    request: Request,
    book_slug: str,
    topic_slug: str,
    data: PracticeSessionStartRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a fixed practice session for a vocabulary topic."""
    user_id = get_user_id_from_request(request)
    return await service.start_session(user_id, book_slug, topic_slug, data, session)


@router.get("/practice-sessions/{session_id}", response_model=PracticeSessionResponse)
async def read_practice_session(
    request: Request,
    session_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Return one practice session owned by the authenticated user."""
    user_id = get_user_id_from_request(request)
    return await service.get_session(user_id, session_id, session)


@router.post("/practice-sessions/{session_id}/attempts", response_model=PracticeSessionResponse)
async def record_practice_session_attempt(
    request: Request,
    session_id: int,
    data: PracticeSessionAttemptRequest,
    session: AsyncSession = Depends(get_session),
):
    """Record one attempt in a practice session."""
    user_id = get_user_id_from_request(request)
    return await service.record_session_attempt(
        user_id, session_id, data, session
    )


@router.post("/practice-sessions/{session_id}/complete", response_model=PracticeSessionResponse)
async def finish_practice_session(
    request: Request,
    session_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Mark a practice session as completed."""
    user_id = get_user_id_from_request(request)
    return await service.complete_session(user_id, session_id, session)
