from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_record,
    async_get_one_record_by,
    async_update_one_record,
)
from app.features.token.model import Token
from app.features.token.schemas import AccessTokenPayload
from app.features.user.model import UserRole
from app.middleware.security import (
    create_access_token,
    create_refresh_token,
    validate_token,
)
from app.utils.constants import TokenType


async def _build_token_payload(
    uid: int,
    email: str,
    refresh_token: str,
    session: AsyncSession,
) -> tuple[AccessTokenPayload, str]:
    """
    Build the payload for the access token.

    Args:
        uid (int): The ID of the user.
        email (str): The email of the user.
        refresh_token (str): The refresh token associated with the user.
        session (AsyncSession): The database session.

    Returns:
        tuple[AccessTokenPayload, str]: A tuple containing the access token payload and the user's role.
    """
    role: UserRole = await async_get_one_record_by(
        UserRole, [UserRole.email == email], session
    )
    payload = AccessTokenPayload(
        user_id=uid,
        user_email=email,
        refresh_token=refresh_token,
        role=role.role
    )
    return payload, role.role


async def generate_tokens(
    session: AsyncSession, uid: int, email: str
) -> tuple[str, str, str]:
    """
    Generate access and refresh tokens for a user.

    Args:
        session (AsyncSession): The database session used for record operations.
        uid (int): The identifier of the user receiving the tokens.
        email (str): The email address encoded in the user's access token.

    Returns:
        tuple[str, str, str]: The access token, the valid refresh token, and the user's
            role name.
    """
    criteria = [Token.user_id == uid, Token.token_type == TokenType.REFRESH.value]
    token = await async_get_one_record_by(
        Token,
        criteria,
        session,
        raise_if_not_found=False,
    )

    if not token:
        refresh_token = create_refresh_token(uid, email)
        await async_create_record(
            Token,
            {
                "user_id": uid,
                "token_type": TokenType.REFRESH.value,
                "token": refresh_token,
            },
            session,
        )
    else:
        refresh_token = token.token
        # validate the refresh token
        valid_token, _ = validate_token(refresh_token)

        if not valid_token:
            # refresh token is expired or invalid, generate a new one
            refresh_token = create_refresh_token(uid, email)
            await async_update_one_record(
                Token, token.id, {"token": refresh_token}, session
            )

    # build access token payload and generate access token
    payload, role = await _build_token_payload(
        uid, email, refresh_token, session
    )
    access_token = create_access_token(data=payload.model_dump())

    return access_token, refresh_token, role
