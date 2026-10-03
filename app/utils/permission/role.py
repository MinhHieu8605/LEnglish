from typing import List, Union
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.async_db import async_get_many_records_by, async_get_one_record_by
from app.features.user.model import User, UserRole
from app.utils.permission._base import _as_list


async def check_user_role(
    user_id: int,
    role: Union[str, List[str]],
    session: AsyncSession,
) -> bool:
    """
    Returns True if the user has the specified role(s), otherwise returns False.

    Args:
        user_id (int): The ID of the user to check.
        role (Union[str, List[str]]): The role(s) to check for. Can be a single role as a string or a list of roles.
        session (AsyncSession): The SQLAlchemy async session for database access.

    Returns:
        bool: True if the user has the specified role(s), otherwise False.
    """
    names = _as_list(role)
    try:
        user = await async_get_one_record_by(
            User,
            [User.id == user_id, User.deleted.is_(False)],
            session,
            raise_if_not_found=False,
        )
        if user is None:
            return False

        roles = await async_get_many_records_by(
            UserRole,
            [UserRole.email == user.email, UserRole.role.in_(names)],
            session,
            raise_if_not_found=False,
        )

        return bool(roles)
    except Exception as e:
        logger.exception(f"Error checking user role: {e}")
        return False
