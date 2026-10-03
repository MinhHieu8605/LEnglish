from datetime import datetime, timedelta, timezone
import math
import secrets
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import asc
from sqlmodel import case
from sqlmodel import desc
from sqlmodel import func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_bulk_records,
    async_get_many_records_by,
    async_get_one_record_by,
)
from app.database.async_db import async_create_record, async_get_one_record_by_id, async_update_one_record
from app.database.async_db import transactional
from app.features.token.service import generate_tokens
from app.features.user.model import User, UserRole
from app.features.user.schemas import Login, Register, UserCreate, UserPaginationFilter, UserResponse, UserUpdate
from app.middleware.security import get_password_hash
from app.utils.common import page_size_to_offset_limit
from app.utils.constants import Message, Role, UserStatus


# ========================
# HELPER
# ========================


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


async def _sync_user_role(user: User, role_value: str, session: AsyncSession) -> None:
    existing = await async_get_one_record_by(
        UserRole,
        [UserRole.email == user.email],
        session,
        raise_if_not_found=False,
    )
    if existing:
        if existing.role != role_value:
            await async_update_one_record(
                UserRole,
                existing.id,
                {"role": role_value},
                session,
            )
    else:
        await async_create_record(
            UserRole,
            {"email": user.email, "role": role_value},
            session,
        )


def _active_user_threshold() -> datetime:
    """
    Calculate the threshold datetime for active users.

    Returns:
        datetime: The threshold datetime for active users, which is 30 days before the current UTC time.
    """
    return datetime.now(tz=timezone.utc) - timedelta(days=30)


# ========================
# User Service
# ========================


class UserService(object):
    @classmethod
    @transactional()
    async def create_new_user_info(
        cls,
        user_in: Register,
        session: AsyncSession,
    ) -> User:
        """
        Create a new user in the database and assign a role to the user.

        Args:
            user_in (Register): The new user data containing email, full name, and password.
            session (AsyncSession): The database session for performing operations.
            request (Request): The HTTP request object (unused in this method).
        
        Returns:
            User: The newly created User object.
        
        Raises:
            HTTPException: If there is an error during the user creation or role assignment process.
        """
        try:
            # Create new user
            user = User(
                email=user_in.email,
                full_name=user_in.full_name,
                lastest_login=datetime.now(timezone.utc),
            )
            user.change_password(user_in.password)

            user_create: User = await async_create_record(
                User,
                {
                    column.name: getattr(user, column.name)
                    for column in User.__table__.columns
                },
                session
            )

            # Assign default role to the new user
            role_value = Role.USER.value
            await _sync_user_role(user, role_value, session)

            await session.refresh(user_create)

            return user_create
        
        except SQLAlchemyError as db_error:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encounter database error while trying create new user. "
                    f"Detail: {db_error}"
                )
            )
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encounter error while trying create new user. "
                    f"Detail: {str(e)}"
                )
            )

    @staticmethod
    @transactional()
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
        
    @staticmethod
    async def _handle_credentials_login(
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
        token_google,
        session: AsyncSession,
        email=None,
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

        if token_google:
            user = await cls._handle_google_login(token_google, session, email=email)
        elif user_in.email and user_in.password:
            user = await cls._handle_credentials_login(user_in, session)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Message.MSG_LOGIN_INVALID_TOKEN_UNAUTHORIZED
            )

        response = await cls._prepare_login_response(user, session)
        
        return response
    
    @staticmethod
    async def _login_with_google(token: str) -> str:
        """
        Logs in a user with a Google OAuth 2.0 token.

        Verifies the token with Google's userinfo endpoint and retrieves
        the user's email address.

        Args:
            token (str): The Google OAuth 2.0 access token.

        Returns:
            str: The user's email address (lowercased).

        Raises:
            HTTPException: If the token is invalid or the API call fails.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="The token is not valid with Google APIs",
                )

            user_info = response.json()
            email = str(user_info.get("email", "")).lower()
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email is None or empty in the response from Google APIs",
                )

            return email
        except HTTPException:
            raise
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error connecting to Google APIs: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during Google login: {str(e)}",
            )

    @classmethod
    async def _handle_google_login(
        cls,
        token_google: str,
        session: AsyncSession,
        email=None,
    ):
        """
        Handle the full Google OAuth login flow.

        Verifies the Google token, finds or auto-creates the user,
        then returns a standard login response with tokens.

        Args:
            token_google (str): The Google OAuth 2.0 access token.
            session (AsyncSession): The database session.
            request (Request): The incoming HTTP request.

        Returns:
            dict: Login response containing access_token, refresh_token, and role.

        Raises:
            HTTPException: If the token is invalid or a database error occurs.
        """
        email = await cls._login_with_google(token=token_google)

        user = await async_get_one_record_by(
            User,
            [User.email == email, User.deleted.is_(False)],
            session,
            raise_if_not_found=False,
        )

        if not user:
            # Auto-create account for first-time Google login.
            # Register.password is required, so generate a random one —
            # Google users will never use password-based login.
            user = await cls.create_new_user_info(
                Register(
                    email=email,
                    full_name=email.split("@")[0],
                    password=secrets.token_hex(16),
                ),
                session,
            )

        return user

    @staticmethod
    async def _prepare_login_response(user, session: AsyncSession):
        """Prepare login response with token."""
        access_token, refresh_token, role = await generate_tokens(
            session=session,
            uid=user.id,
            email=user.email
        )
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "deleted": user.deleted,
            "role": role,
            "refresh_token": refresh_token,
            "access_token": access_token,
        }

    @staticmethod
    async def request_event(session: AsyncSession, email: str, last_login=None):
        """
        Requests an event for a user, updating request counts and timestamps.

        Args:
            session: The database session.
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
        user.lastest_request = datetime.now(tz=timezone.utc)

        # Commit the changes to the database
        await session.commit()
        await session.refresh(user)

    @classmethod
    async def register(
        cls,
        user_in: Register,
        session: AsyncSession,
    ):
        """
        Register a new user in the system.

        Args:
            user_in (Register): The user registration data.
            session (AsyncSession): The database session for performing operations.
        
        Returns:
            dict: A dictionary containing the access token and its expiration time.
        
        Raises:
            HTTPException: If the registration data is invalid or if there is an error during the registration process.
        """
        try:
            is_user = await async_get_one_record_by(
                User,
                [func.lower(User.email) == user_in.email.lower()],
                session,
                raise_if_not_found=False,
            )
            if is_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=Message.MSG_REGISTER_EMAIL_EXIST
                )
            
            # create user
            dbuser = await cls.create_new_user_info(user_in, session)

            return await _build_user_response(dbuser, session)
        
        except HTTPException:
            raise
        except SQLAlchemyError as db_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encounter database error while trying add role when create new user. "
                    f"Detail: {db_error}"
                )
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encounter error while trying add role when create new user. "
                    f"Detail: {str(e)}"
                )
            )

    @staticmethod
    def _build_where_clauses(filters: UserPaginationFilter, active_status=None):
        """
        Construct a list of SQLAlchemy filter conditions based on the provided filters.

        Args:
            filters (UserPaginationFilter): An object containing filter criteria for querying users.
            active_status (bool, optional): A SQLAlchemy case expression for checking active status.
        
        Returns:
            list: A list of SQLAlchemy filter conditions to be used in a query.
        """
        where_clause = [User.deleted.is_(False)]
        for key, value in filters.model_dump(
            exclude_unset=True, exclude_none=True,
        ).items():
            if key == "keyword":
                where_clause.append(User.email.ilike(f"%{value.strip()}%") | User.full_name.ilike(f"%{value.strip()}%"))
            elif key == "role":
                where_clause.append(UserRole.role == value.value)
            elif key == "status" and active_status is not None:
                where_clause.append(
                    active_status.is_(value = UserStatus.ACTIVE.value)
                )
        return where_clause
    
    @staticmethod
    def _process_user_record(
        data: list[Tuple[User, str, bool]],
    ) -> List[Dict[str, Any]]:
        """
        Transform a list of tuples containing User, role, and status into a list of dictionaries.

        Each item in the input data is expected to be a tuple containing:
            - item[0]: A User object.
            - item[1]: A string representing the user's role.
            - item[2]: A boolean indicating the user's status (active/inactive).

        Args:
            data (list[Tuple[User, str, bool]]): A list of tuples where each tuple contains a User object,
        """
        return [
            {
                "id": item[0].id,
                "email": item[0].email,
                "full_name": item[0].full_name,
                "role": item[1] or "user",
                "lastest_login": item[0].lastest_login,
                "lastest_request": item[0].lastest_request,
                "created_time": item[0].created_time,
                "active": item[2],
            }
            for item in data
        ]
    
    @staticmethod
    async def _count_users_by_role(session: AsyncSession) -> Dict[str, int]:
        """
        Count the number of users for each role in the system.

        Args:
            session (AsyncSession): The database session for performing operations.

        Returns:
            dict: A dictionary containing the count of users for each role.
        """
        try:
            statement = (
                select(UserRole.role, func.count(UserRole.email))
                .join(User, User.email == UserRole.email)
                .where(User.deleted.is_(False))
                .group_by(UserRole.role)
            )
            result = await session.exec(statement)
            rows = result.all()

            return {role: count for role, count in rows}
        except SQLAlchemyError as db_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encounter database error while trying count users by role. "
                    f"Detail: {db_error}"
                )
            )
    
    @staticmethod
    async def _count_active_users(session: AsyncSession) -> int:
        """
        Counts users who have logged in or made a request within the last 30 minutes.

        Args:
            request (Request): The HTTP request object.
            session (AsyncSession): SQLAlchemy async session.

        Returns:
            int: Number of active users.
        """
        try:
            threshold = _active_user_threshold()

            stmt = select(func.count(User.id)).where(
                or_(
                    User.lastest_login >= threshold,
                    User.lastest_request >= threshold,
                ),
                User.deleted.is_(False),
            )

            result = await session.exec(stmt)
            count = result.one()
            return count
        except SQLAlchemyError as db_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encounter database error while trying to count active users. "
                    f"Detail: {db_error}"
                )
            )

    @classmethod
    async def _get_user_statistics_data(
        cls, 
        request: Request, 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Asynchronously retrieves statistical data about users in the system.

        This method calculates:
        - The total number of users.
        - The number of users grouped by their roles.
        - The number of active users.
        - The number of deactivated users (derived from total - active).

        It handles potential database errors and logs them appropriately.

        Args:
            request (Request): The incoming HTTP request object, used for
                logging context.
            session (AsyncSession): The SQLAlchemy asynchronous session for
                database operations.

        Returns:
            dict: A dictionary containing:
                - "total_user" (int): Total number of users.
                - "users_by_role" (Dict[str, int]): Mapping of user roles to
                    their respective counts.
                - "number_active" (int): Count of active users.
                - "number_inactive" (int): Count of inactive users.

        Raises:
            SQLAlchemyError: If a database-related error occurs.
            Exception: For any other unexpected errors.
        """
        try:
            # Count total users by role
            roles_count = await cls._count_users_by_role(session)
            total_user = sum(roles_count.values())

            # Count active users
            active_count = await cls._count_active_users(session)

            return {
                "total_user": total_user,
                "user_by_role": roles_count,
                "number_active": active_count,
                "number_inactive": total_user - active_count,
            }
        except SQLAlchemyError as db_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encountered database error while trying to get user statistics"
                    f"Detail: {db_error}"
                )
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encountered error while trying to get user statistics"
                    f"Detail: {e}"
                )
            )

    @classmethod
    async def get_user_management(
        cls,
        filters: UserPaginationFilter,
        request: Request,
        session: AsyncSession,
    ):
        """
        Retrieves a paginated list of users based on the provided filters.

        This method applies filters for role, status, and keyword search, and
        supports pagination through the use of `skip` and `limit` parameters.

        Args:
            request (Request): The incoming HTTP request object.
            session (AsyncSession): The SQLAlchemy asynchronous session for
                database operations.
            filters (UserPaginationFilter): An object containing the filtering
                criteria for the user query.

        Returns:
            Tuple[
                List[Dict[str, Any]],   # List of users
                int,                    # Total number of users
                int,                    # Total number of pages
                Dict[str, int],         # User statistical summary
            ]

        Raises:
            SQLAlchemyError: If a database-related error occurs during the query execution.
            Exception: For any other unexpected errors encountered.
        """
        try:
            # Get statistical data
            statistical_summary = await cls._get_user_statistics_data(request, session)
            
            # Check if user is active or not
            time_threshold = _active_user_threshold()
            active_status = case(
                (
                    or_(
                        User.lastest_login >= time_threshold,
                        User.lastest_request >= time_threshold,
                    ),
                    True
                ),
                else_=False
            )

            # Build where clauses and query
            where_clauses = cls._build_where_clauses(filters, active_status)
            query = (
                select(User, UserRole.role, active_status.label("is_active"))
                .join(UserRole, User.email == UserRole.email, isouter=True)
                .where(*where_clauses)
            )
            
            # Total users matching filters
            count_query = (
                select(func.count(User.id))
                .join(UserRole, User.email == UserRole.email, isouter=True)
                .where(*where_clauses)
            )
            total_users = (await session.exec(count_query)).one()

            # Sorting
            if filters.sorted_by:
                sort_column = getattr(User, filters.sorted_by, None)
                if sort_column is not None:
                    query = query.order_by(
                        desc(sort_column)
                        if filters.sorted_order == "descend"
                        else asc(sort_column)
                    )
            
            # Pagination
            pages = None
            if filters.page_size and filters.page:
                pages = -(-total_users // filters.page_size)
                offset, limit = page_size_to_offset_limit(filters.page, filters.page_size)
                query = query.offset(offset).limit(limit)
            result = await session.exec(query)
            users = result.all()

            # Process data and return 
            processed_users = cls._process_user_record(users)

            return (
                processed_users, 
                total_users,
                pages,
                {
                    "total_user" : statistical_summary["total_user"],
                    "user_by_role" : statistical_summary["user_by_role"],
                    "number_active" : statistical_summary["number_active"],
                    "number_inactive" : statistical_summary["number_inactive"],
                }
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Encountered error while trying to get user management "
                    f"Detail: {e}"
                )
            )
    
    @staticmethod
    async def get_user_by_id(user_id: int, session: AsyncSession) -> UserResponse:
        """
        Retrieve a user by their ID.

        Args:
            user_id (int): The ID of the user to retrieve.
            session (AsyncSession): The database session for performing operations.

        Returns:
            UserResponse: A response object containing user details.

        Raises:
            HTTPException: If the user is not found or if there is an error during the retrieval process.
        """
        user = await async_get_one_record_by(
            User,
            [User.id == user_id, User.deleted.is_(False)],
            session,
            raise_if_not_found=False,
        )
        if user is None or user.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        return await _build_user_response(user, session)

    @staticmethod
    @transactional()
    async def update_user(user_id: int, data: UserUpdate, session: AsyncSession) -> UserResponse:
        """
        Update a user's information.

        Args:
            user_id (int): The ID of the user to update.
            data (UserUpdate): The new data for the user.
            session (AsyncSession): The database session for performing operations.

        Returns:
            UserResponse: A response object containing the updated user details.

        Raises:
            HTTPException: If the user is not found or if there is an error during the update process.
        """
        user = await async_get_one_record_by_id(
            User,
            user_id,
            session,
            raise_if_not_found=False,
        )
        if user is None or user.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        update_fields: dict = {}

        if data.role is not None:
            await _sync_user_role(user, data.role.value, session)

        if data.full_name is not None:
            update_fields["full_name"] = data.full_name

        if data.password is not None:
            update_fields["password"] = get_password_hash(data.password)

        if update_fields:
            user = await async_update_one_record(
                User,
                user_id,
                update_fields,
                session,
            )

        return await _build_user_response(user, session)

    @staticmethod
    @transactional()
    async def delete_user(
        user_id: int, 
        session: AsyncSession, 
        current_user_id: Optional[int] = None,
    ) -> None:
        """
        Soft delete a user by setting the 'deleted' flag to True.

        Args:
            user_id (int): The ID of the user to delete.
            session (AsyncSession): The database session for performing operations.
            current_user_id (Optional[int]): The ID of the currently logged-in user. Defaults to None.

        Raises:
            HTTPException: If the user is not found, if the user is trying to delete themselves, or if there is an error during the deletion process.
        """
        if current_user_id is not None and user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own account"
            )

        user = await async_get_one_record_by_id(
            User,
            user_id,
            session,
            raise_if_not_found=False,
        )
        if user is None or user.deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )
        
        await async_update_one_record(
            User,
            user_id,
            {"deleted": True},
            session,
        )
