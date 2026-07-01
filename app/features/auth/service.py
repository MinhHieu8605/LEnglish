from sqlmodel import func
from datetime import timezone, datetime
from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder

from app.database.async_db import async_get_one_record_by
from app.features.auth.schemas import Login
from app.features.token.service import generate_tokens
from app.features.user.model import User
from sqlmodel.ext.asyncio.session import AsyncSession

from app.utils.constants import Message


class AuthService(object):
    """
    Service class for authentication-related operations.
    """
    @classmethod
    async def _handle_credentials_login(
        cls, 
        user_in: Login, 
        session: AsyncSession
    ) -> User:
        """
        Process email and password login credentials.
        """
        user: User = await async_get_one_record_by(
            User,
            [User.email == user_in.email, User.deleted.is_(False)],
            session,
            raise_if_not_found=False,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Message.MSG_LOGIN_WRONG_EMAIL
            )

        if not user_in.password or not user.check_password(user_in.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Message.MSG_LOGIN_WRONG_PASSWORD
            )
        
        return user

    @classmethod
    async def handle_login_process(
        cls,
        user_in: Login,
        session: AsyncSession,
    ):
        """
        Handle the user login process, including credential validation and token generation.

        Args:
            user_in (Login): The user login credentials.
            session (AsyncSession): The database session for performing operations.        
        Returns:
            dict: A dictionary containing the access token and its expiration time.
        
        Raises:
            HTTPException: If the login credentials are invalid or if there is an error during the login process.
        """
        user = None

        if user_in.email and user_in.password:
            user = await cls._handle_credentials_login(user_in, session)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Message.MSG_LOGIN_INVALID_TOKEN_UNAUTHORIZED
            )

        response = await cls._prepare_login_response(user, session)
        
        return response
    
    @staticmethod
    async def _prepare_login_response(user, session: AsyncSession):
        """Prepare login response with token."""
        user_response = jsonable_encoder(user)
        access_token, refresh_token, role = await generate_tokens(
            session=session,
            uid=user.id,
            email=user.email
        )
        user_response["access_token"] = access_token
        user_response["refresh_token"] = refresh_token
        user_response["role"] = role

        del user_response["password"]  # Remove password from response for security

        return user_response

    @classmethod
    async def request_event(cls, session: AsyncSession, email: str, last_login=None):
        """
        Requests an event for a user, updating request counts and timestamps.

        Args:
            db_session: The database session.
            email: The email address of the user.
            last_login: Optional last login time to update.  Defaults to None.

        Raises:
            ValueError: If the user with the given email is not found.

        Returns:
            None.  The function updates the user object in the database.
        """
        user = await async_get_one_record_by(
            User, [func.lower(User.email) == email.lower()], session
        )

        user.lastest_login = last_login or user.lastest_login

        # Commit the changes to the database
        await session.commit()
        await session.refresh(user)
