from typing import Optional

from fastapi import HTTPException, Header, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import async_get_one_record_by_id, get_session
from app.features.token.schemas import AccessTokenPayload
from app.features.user.model import User
from app.middleware.security import validate_token
from app.utils.util import get_token_from_request


async def _check_user_exist(user_id: int, session: AsyncSession) -> bool:
    """
    Checks if a user exists in the database.

    Args:
        user_id (int): The ID of the user to check.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the user exists, False otherwise.
    """
    user = await async_get_one_record_by_id(
        User, user_id, session, raise_if_not_found=False
    )
    return bool(user) and not getattr(user, "deleted", False)


async def get_current_user(request: Request, token: Optional[str] = Header(None)):
    """
    FastAPI dependency that validates the bearer token and populates request.state.user 
    with the current user.

    Raises:
        HTTPException: If the token is invalid or the user does not exist.
    """
    token = get_token_from_request(request)
    valid_token, data = validate_token(token)
    
    async for session in get_session():
        user_exists = await _check_user_exist(int(data.get("user_id", 0)), session)
    
    if not valid_token or not user_exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or user does not exist.",
        )
    
    # Populate request.state.user with the current user
    token_data = AccessTokenPayload(**data)

    # Set the user information in request.state for downstream access
    request.state.email = token_data.user_email
    request.state.user_id = token_data.user_id
    request.state.role = token_data.role
