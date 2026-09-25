from typing import List

from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.vocabulary.schemas import (
    TopicWordResponse,
    VocabularyBookResponse,
    VocabularyTopicResponse,
)
from app.features.vocabulary.service import VocabularyService
from app.utils.common import get_user_id_from_request

router = APIRouter()


@router.get(
    "/books",
    response_model=List[VocabularyBookResponse],
    summary="Get all vocabulary books",
)
async def get_books(
    session: AsyncSession = Depends(get_session),
):
    """Get all active curated vocabulary collections."""
    return await VocabularyService.get_books(session)


@router.get(
    "/books/{book_slug}/topics",
    response_model=List[VocabularyTopicResponse],
    summary="Get book topics with user progress stats",
)
async def get_book_topics(
    request: Request,
    book_slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get topics in one curated collection with user progress."""
    user_id = get_user_id_from_request(request)
    return await VocabularyService.get_book_topics(user_id, book_slug, session)


@router.get(
    "/books/{book_slug}/topics/{topic_slug}/words",
    response_model=List[TopicWordResponse],
    summary="Get words in a book topic with user progress",
)
async def get_book_topic_words(
    request: Request,
    book_slug: str,
    topic_slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get words only when both slugs identify the same active book/topic."""
    user_id = get_user_id_from_request(request)
    return await VocabularyService.get_book_topic_words(
        user_id, book_slug, topic_slug, session
    )


@router.get(
    "/topics/{topic_slug}/words",
    response_model=List[TopicWordResponse],
    summary="Get topic words with user progress",
)
async def get_topic_words(
    request: Request,
    topic_slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get words in one curated vocabulary topic."""
    user_id = get_user_id_from_request(request)
    return await VocabularyService.get_topic_words(user_id, topic_slug, session)
