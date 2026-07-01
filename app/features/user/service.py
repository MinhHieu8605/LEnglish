from typing import List

from fastapi import HTTPException, status

from app.database.async_db import async_create_bulk_records, async_get_many_records_by, async_get_one_record_by
from app.features.user.model import User, UserRole
from app.features.user.schemas import UserCreate, UserResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.middleware.security import get_password_hash
from app.utils.constants import Role


async def _build_user_response(user: User, session: AsyncSession) -> UserResponse:
    """
    Build a UserResponse object from a User model instance.
    """
    # Query UserRole to get the user's role
    user_role = await async_get_one_record_by(
        UserRole,
        [UserRole.email == user.email],
        session,
        raise_if_not_found=False,
    )

    # Get role value, default to USER if not found
    if user_role:
        role_value = user_role.role
    else:
        role_value = Role.USER.value

    # Build and return the UserResponse
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=Role(role_value) if isinstance(role_value, str) else role_value,
        deleted=user.deleted,
        created_time=user.created_time,
        updated_time=user.updated_time,
    )


class UserService(object):
    @staticmethod
    async def create_user(
        data: UserCreate,
        session: AsyncSession,
    ) -> List[UserResponse]:
        """
        Create one or more users accounts with the specified details.
        """
        
        # Validate the number of emails / full names
        if len(data.email) != len(data.full_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of emails must match number of full names",
            )
        
        # Check email 
        existing_users = await async_get_many_records_by(
            User,
            [User.email.in_(data.email)],
            session,
            raise_if_not_found=False,
        )
        
        if existing_users:
            conflicts = [u.email for u in existing_users]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {conflicts} already exist"
            )
        
        # Bulk-create all User rows in one transaction
        user_data_list = [
            {
                "email": email,
                "full_name": full_name,
                "deleted": False,
                **(
                    {"password": get_password_hash(data.password)} 
                    if data.password is not None
                    else {}
                ),
            }
            for email, full_name in zip(data.email, data.full_name)
        ]
        users: List[User] = await async_create_bulk_records(
            User, user_data_list, session,
        )

        # Create UserRole
        await async_create_bulk_records(
            UserRole,
            [{"email": email, "role": data.role.value} for email in data.email],
            session,
        )

        return [await _build_user_response(user, session) for user in users]
