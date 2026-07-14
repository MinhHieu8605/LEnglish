from typing import List
from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.vocabulary.schemas import (
    VocabularyItemResponse,
    NotebookVocabularyItemResponse,
    VocabularyListFilter,
    VocabularyListMeta,
    VocabularyListResponse,
    VocabularyReviewDueResponse,
    VocabularyReviewRequest,
    VocabularySaveRequest,
    VocabularyBookResponse,
    VocabularyTopicResponse,
    TopicWordResponse,
)
from app.features.vocabulary.service import VocabularyService
from app.utils.common import get_user_id_from_request

router = APIRouter()


@router.post(
    "/save/{notebook_id}",
    response_model=List[NotebookVocabularyItemResponse],
    status_code=201,
    summary="Save a word to a notebook",
)
async def save_word(
    request: Request,
    notebook_id: int,
    data: VocabularySaveRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Save a word to a specific vocabulary notebook.

    If the word already has multiple global entries, all of them are reused.
    Otherwise, entries are created from the dictionary meanings in the request.
    Creates notebook items and initialises spaced-repetition progress.
    When source_subtitle_id is provided, the stored subtitle text is used as
    the trusted context sentence.
    """
    user_id = get_user_id_from_request(request)
    result = await VocabularyService.save_word(user_id, notebook_id, data, session)
    return result


@router.get(
    "",
    response_model=VocabularyListResponse,
    summary="List saved vocabulary",
)
async def list_words(
    request: Request,
    filters: VocabularyListFilter = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    List the authenticated user's saved vocabulary.

    Supports pagination, filtering by learning status, and keyword search
    against the word text or its normalized form.

    Args:
        filters (VocabularyListFilter): Pagination and filter parameters.

    Returns:
        VocabularyListResponse: Paginated list of vocabulary items.
    """
    user_id = get_user_id_from_request(request)
    items, total, pages = await VocabularyService.list_words(user_id, filters, session)
    return VocabularyListResponse(
        data=items,
        meta=VocabularyListMeta(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        ),
    )


@router.post(
    "/{vocabulary_id}/review",
    response_model=VocabularyItemResponse,
    summary="Review and update spaced repetition",
)
async def review_word(
    request: Request,
    vocabulary_id: int,
    data: VocabularyReviewRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Review a vocabulary word and update its spaced repetition schedule.

    Uses interval progression: 1 → 3 → 7 → 14 → 30 days.
    - **correct** → advances to next interval
    - **wrong** → resets count and goes back to 1 day

    Args:
        vocabulary_id (int): The vocabulary ID to review.
        data (VocabularyReviewRequest): The review result (correct/wrong).

    Returns:
        VocabularyItemResponse: The updated vocabulary item.

    Raises:
        404: If the word is not in the user's vocabulary.
    """
    user_id = get_user_id_from_request(request)
    return await VocabularyService.review_word(user_id, vocabulary_id, data.rating, session)


@router.get(
    "/due",
    response_model=VocabularyReviewDueResponse,
    summary="Get words due for review",
)
async def get_due_words(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Get vocabulary words due for review for the authenticated user.

    Words due for review are those whose next_review_at is in the past or
    null. Excludes mastered and ignored words. Ordered by oldest due first.

    Returns:
        VocabularyReviewDueResponse: List of due words and total count.
    """
    user_id = get_user_id_from_request(request)
    items, total_due = await VocabularyService.get_due_words(user_id, session)
    return VocabularyReviewDueResponse(data=items, total_due=total_due)


@router.get(
    "/books",
    response_model=List[VocabularyBookResponse],
    summary="Get all vocabulary books",
)
async def get_books(
    session: AsyncSession = Depends(get_session),
):
    """
    Get all active vocabulary books/collections.
    Ordered by creation date ascending.
    """
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
    """
    Get all topics belonging to a book.
    Includes count of mastered and learning words per topic for the user.
    """
    user_id = get_user_id_from_request(request)
    return await VocabularyService.get_book_topics(user_id, book_slug, session)


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
    """
    Get all words inside a topic.
    Includes the user's progress/repetition stats for each word.
    """
    user_id = get_user_id_from_request(request)
    return await VocabularyService.get_topic_words(user_id, topic_slug, session)
