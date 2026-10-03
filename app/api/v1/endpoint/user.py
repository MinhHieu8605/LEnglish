from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.user.schemas import Login, Register, UserCreate, UserResponse, UserUpdate
from app.features.user.schemas import ManagementResponseMetadata
from app.features.user.schemas import PaginatedUserListResponse
from app.features.user.schemas import UserPaginationFilter
from app.features.user.schemas import UserStatisticSummaryResponse
from app.features.user.service import UserService
from app.utils.common import get_user_id_from_request
from app.utils.constants import Message, Role
from app.utils.permission.enforcer import Policy, PolicyEnforcer

public_router = APIRouter()
router = APIRouter()


@public_router.post("/login")
async def login(
    user_in: Optional[Login] = None,
    token_google: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Handle user login and return an access token.

    This endpoint processes user login requests. It accepts user credentials, 
    verifies them, and returns an access token if the credentials are valid.

    Args:
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
        if user_in is None and not token_google:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Message.MSG_LOGIN_INVALID_TOKEN
            )

        user = await UserService.handle_login_process(
            user_in or Login(),
            token_google,
            session,
            email=email
        )
        await UserService.request_event(
            session, user["email"], datetime.now(tz=timezone.utc)
        )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error with {e}",
        )


@public_router.post("/logout")
async def logout():
    """
    User logout endpoint.
    """
    return {"message": Message.MSG_LOGOUT_SUCCESS}


@public_router.post("/register")
async def register(
    user_in: Register,
    session: AsyncSession = Depends(get_session)
) -> UserResponse:
    """
    Register a new user in the system.
    """
    return await UserService.register(user_in, session)


@router.post(
    "",
    response_model=List[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create user"
)
@PolicyEnforcer.required(Policy.role(Role.ADMIN))
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create one or more users accounts with the specified details.
    """
    return await UserService.create_user(data, session)


@router.get(
    "/user_management",
    response_model=PaginatedUserListResponse,
    summary="Get all users"
)
@PolicyEnforcer.required(Policy.role(Role.ADMIN))
async def list_users(
    request: Request,
    filters: UserPaginationFilter = Depends(),
    session: AsyncSession = Depends(get_session)
) -> PaginatedUserListResponse:
    """
    Get all users with pagination and filtering.
    """
    data, total, pages, stats_summary = await UserService.get_user_management(
        filters, request, session
    )
    
    return PaginatedUserListResponse(
        data=data,
        statistic_summary=UserStatisticSummaryResponse(
            total_user=stats_summary["total_user"],
            user_by_role=stats_summary["user_by_role"],
            number_active=stats_summary["number_active"],
            number_inactive=stats_summary["number_inactive"],
        ),
        metadata=ManagementResponseMetadata(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages
        ),
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID"
)
async def get_user_by_id(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieve a user by their ID.
    """
    return await UserService.get_user_by_id(user_id, session)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user"
)
async def update_user(
    user_id: int,
    data: UserUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    Update a user's information.
    """
    return await UserService.update_user(user_id, data, session)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user"
)
@PolicyEnforcer.required(Policy.role(Role.ADMIN))
async def delete_user(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a user by their ID.
    """
    current_user_id = get_user_id_from_request(request)
    await UserService.delete_user(user_id, session, current_user_id=current_user_id)
