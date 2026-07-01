from app.database.async_db import get_session
from fastapi import Depends
from app.features.user.schemas import UserCreate
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import status
from app.features.user.schemas import UserResponse
from typing import List
from fastapi import APIRouter

from app.features.user.service import UserService


user_router = APIRouter()


@user_router.post(
    "",
    response_model=List[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create user"
)
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create one or more users accounts with the specified details.
    """
    return await UserService.create_user(data, session)
