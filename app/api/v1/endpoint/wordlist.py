from typing import List

from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.wordlist.schemas import (
    ReviewSavedWordRequest,
    SavedWordFilter,
    SavedWordListMeta,
    SavedWordListResponse,
    SavedWordResponse,
    SavedWordReviewResponse,
    SavedWordsDueFilter,
    SavedWordsDueResponse,
    SaveWordRequest,
)
from app.features.wordlist.service import WordListService
from app.utils.common import get_user_id_from_request

router = APIRouter()


@router.post(
    "/{word_list_id}/words",
    response_model=List[SavedWordResponse],
    status_code=201,
    summary="Save a word to a word list",
)
async def save_word(
    request: Request,
    word_list_id: int,
    data: SaveWordRequest,
    session: AsyncSession = Depends(get_session),
):
    """Save all available word types to a user's word list.

    Args:
        request (Request): Authenticated HTTP request.
        word_list_id (int): Identifier of the destination word list.
        data (SaveWordRequest): Word, meanings, and optional context data.
        session (AsyncSession): Active database session.

    Returns:
        List[SavedWordResponse]: All entries saved for the word.
    """
    user_id = get_user_id_from_request(request)
    return await WordListService.save_word(user_id, word_list_id, data, session)


@router.get(
    "/{word_list_id}/words",
    response_model=SavedWordListResponse,
    summary="List words saved in a word list",
)
async def list_saved_words(
    request: Request,
    word_list_id: int,
    filters: SavedWordFilter = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """List words explicitly saved in a selected word list.

    Args:
        request (Request): Authenticated HTTP request.
        word_list_id (int): Identifier of the selected word list.
        filters (SavedWordFilter): Pagination and keyword filters.
        session (AsyncSession): Active database session.

    Returns:
        SavedWordListResponse: Paginated saved words and metadata.
    """
    user_id = get_user_id_from_request(request)
    items, total, pages = await WordListService.get_saved_words(
        user_id, word_list_id, filters, session
    )
    return SavedWordListResponse(
        data=items,
        metadata=SavedWordListMeta(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        ),
    )


@router.post(
    "/{word_list_id}/words/{vocabulary_id}/review",
    response_model=SavedWordReviewResponse,
    summary="Review a word saved in a word list",
)
async def review_saved_word(
    request: Request,
    word_list_id: int,
    vocabulary_id: int,
    data: ReviewSavedWordRequest,
    session: AsyncSession = Depends(get_session),
):
    """Submit an SRS rating for a saved word.

    Args:
        request (Request): Authenticated HTTP request.
        word_list_id (int): Identifier of the selected word list.
        vocabulary_id (int): Identifier of the reviewed vocabulary entry.
        data (ReviewSavedWordRequest): Selected SRS rating.
        session (AsyncSession): Active database session.

    Returns:
        SavedWordReviewResponse: Saved word with updated SRS progress.
    """
    user_id = get_user_id_from_request(request)
    return await WordListService.review_saved_word(
        user_id, word_list_id, vocabulary_id, data.rating, session
    )


@router.get(
    "/{word_list_id}/review/due",
    response_model=SavedWordsDueResponse,
    summary="Get saved words due for review",
)
async def get_saved_words_due(
    request: Request,
    word_list_id: int,
    filters: SavedWordsDueFilter = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """Get words currently due in a selected word list.

    Args:
        request (Request): Authenticated HTTP request.
        word_list_id (int): Identifier of the selected word list.
        filters (SavedWordsDueFilter): Pagination parameters.
        session (AsyncSession): Active database session.

    Returns:
        SavedWordsDueResponse: Due words and their total count.
    """
    user_id = get_user_id_from_request(request)
    items, total, pages = await WordListService.get_saved_words_due(
        user_id, word_list_id, filters, session
    )
    return SavedWordsDueResponse(
        data=items,
        metadata=SavedWordListMeta(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        ),
    )
