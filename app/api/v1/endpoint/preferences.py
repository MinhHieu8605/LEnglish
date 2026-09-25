from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.preferences.schemas import (
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from app.features.preferences.service import UserPreferencesService
from app.utils.common import get_user_id_from_request


router = APIRouter()


@router.get("", response_model=UserPreferencesResponse)
async def get_preferences(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await UserPreferencesService.get_preferences(
        get_user_id_from_request(request), session
    )


@router.put("", response_model=UserPreferencesResponse)
async def update_preferences(
    data: UserPreferencesUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await UserPreferencesService.update_preferences(
        get_user_id_from_request(request), data, session
    )
