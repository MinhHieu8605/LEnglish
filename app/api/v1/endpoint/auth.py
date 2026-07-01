from loguru import logger
from datetime import timezone
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.auth.schemas import Login

from app.features.auth.service import AuthService
from app.utils.constants import Message

auth_router = APIRouter()


@auth_router.post("/login")
async def login(
    user_in: Login = None,
    token: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Handle user login and return an access token.

    This endpoint processes user login requests. It accepts user credentials, 
    verifies them, and returns an access token if the credentials are valid.

    Args:
        request (Request): The incoming HTTP request.
        response (Response): The HTTP response to be sent back.
        user_in (Login, optional): The user login credentials. Defaults to None.
        token (str, optional): An optional token provided in the request header. Defaults to None.
        session (AsyncSession): The database session for performing operations.
    
    Returns:
        dict: A dictionary containing the access token and its expiration time.

    Raises:
        HTTPException: If the login credentials are invalid or if there is an error during the login process.
    """
    email = user_in.email if user_in is not None else None
    if email and "@" not in email:
        email = None
    
    try:
        if user_in is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Message.MSG_LOGIN_INVALID_TOKEN
            )
        
        user = await AuthService.handle_login_process(
            user_in=user_in,
            session=session,
        )
        await AuthService.request_event(
            session, user["email"], datetime.now(tz=timezone.utc)
        )
        return user
    except Exception as e:
        logger.error(f"Exception during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error with {e}",
        )


@auth_router.post("/logout")
async def logout():
    """
    User logout endpoint.
    """
    return {"message": Message.MSG_LOGOUT_SUCCESS}
