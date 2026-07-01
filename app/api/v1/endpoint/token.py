from app.database.async_db import get_session
from fastapi import Depends, HTTPException
from fastapi import APIRouter, Body, status

from sqlmodel.ext.asyncio.session import AsyncSession
from app.features.token.schemas import AccessTokenResponse
from app.features.token.service import _build_token_payload
from app.middleware.security import create_access_token, validate_token


token_router = APIRouter()


@token_router.post(
    "/access", status_code=status.HTTP_200_OK, response_model=AccessTokenResponse
)
async def generate_access_token(
    refresh_token: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_session)
):
    """
    Generate an access token for the user.
    """
    # validate the refresh token
    valid_token, token_raw = validate_token(refresh_token)

    if not valid_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    # build access token payload and generate access token
    payload, role = await _build_token_payload(
        token_raw["user_id"],
        token_raw["user_email"],
        refresh_token,
        session=session
    )
    access_token = create_access_token(data=payload.model_dump())

    return AccessTokenResponse(
        id=token_raw["user_id"],
        email=token_raw["email"],
        refresh_token=refresh_token,
        access_token=access_token,
        role=role
    )