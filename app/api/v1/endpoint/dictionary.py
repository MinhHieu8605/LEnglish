from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.dictionary.schemas import DictionaryLookupResponse
from app.features.dictionary.service import DictionaryService

router = APIRouter()


@router.get(
    "/lookup",
    response_model=DictionaryLookupResponse,
    summary="Look up a word in the dictionary",
)
async def lookup(
    word: str = Query(..., min_length=1, max_length=100),
    session: AsyncSession = Depends(get_session),
):
    """
    Look up a word using the local vocabulary database or AI dictionary.

    Free Dictionary API is used opportunistically for phonetics and audio.

    Args:
        word (str): The word to look up. Must be between 1 and 100 characters.

    Returns:
        DictionaryLookupResponse: Parsed dictionary entry.

    Raises:
        502: Dictionary service returned invalid data.
        503: AI dictionary service is unavailable.
    """
    return await DictionaryService.lookup(word, session)
