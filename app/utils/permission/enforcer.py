from functools import wraps
from typing import Callable, List, Optional, Union

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.async_db import get_session
from app.utils.common import get_user_id_from_request
from app.utils.permission._base import _as_list
from app.utils.permission.role import check_user_role


class Policy(object):
    """
    An atomic authorization policy
    """

    def __init__(self, names: List[str]) -> None:
        self.names = names

    @classmethod
    def role(cls, name: Union[str, List[str]]) -> "Policy":
        """
        Create a policy that requires the user to have a specific role or roles.
        """
        return cls(_as_list(name))

    async def check(self, user_id: int, session: AsyncSession) -> bool:
        """
        Evaluate the policy for a given user ID and session.
        """
        return await check_user_role(user_id, self.names, session)

    def __repr__(self) -> str:
        return f"Policy(role, {self.names!r})"

    @property
    def name(self) -> List[str]:
        return self.names


class PolicyEnforcer:
    """
    HTTP authorization policy enforcer for FastAPI endpoints.
    """

    @staticmethod
    async def check(
        user_id: int, 
        policy: Policy, 
        session: AsyncSession
    ) -> bool:
        """
        Check if the user satisfies the given policy.
        """
        return await policy.check(user_id, session)

    @staticmethod
    async def check_all(
        user_id: int, 
        policies: List[Policy], 
        session: AsyncSession
    ) -> bool:
        """
        Check if the user satisfies all given policies.
        """
        for policy in policies:
            if not await policy.check(user_id, session):
                return False
        return True

    @staticmethod
    def require(policy: Policy) -> Callable:
        """
        FastAPI dependency that enforces the given policy for the current user.

        Args:
            policy (Policy): The policy to enforce.

        Returns:
            Callable: A FastAPI dependency function that checks the policy for the current user.

        Example:
            _: None = Depends(PolicyEnforcer.require(
                Policy.role(Role.ADMIN),
            ))
        """

        async def _dependency(
            request: Request,
            session: AsyncSession = Depends(get_session),
        ) -> None:
            """
            Enforce the policy for the current user.

            Args:
                request (Request): The FastAPI request object.
                session (AsyncSession): The SQLAlchemy async session for database access.

            Raises:
                HTTPException: If the user does not satisfy the policy.
            """
            user_id = get_user_id_from_request(request)

            if not await policy.check(user_id, session):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this resource.",
                )

        return _dependency

    @staticmethod
    def require_all(*policies: Policy) -> Callable:
        """
        FastAPI dependency that enforces all given policies for the current user.

        Args:
            *policies (Policy): A variable number of Policy instances to enforce.

        Returns:
            Callable: A FastAPI dependency function that checks all policies for the current user.

        Example:
            _: None = Depends(PolicyEnforcer.require_all(
                Policy.role(Role.ADMIN),
            ))
        """

        async def _dependency(
            request: Request,
            session: AsyncSession = Depends(get_session),
        ) -> None:
            """
            Enforce all policies for the current user.

            Args:
                request (Request): The FastAPI request object.
                session (AsyncSession): The SQLAlchemy async session for database access.

            Raises:
                HTTPException: If the user does not satisfy all policies.
            """
            user_id = get_user_id_from_request(request)

            for policy in policies:
                if not await policy.check(user_id, session):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You do not have permission to access this resource.",
                    )

        return _dependency

    @staticmethod
    def required(policy: Policy) -> Callable:
        """
        FastAPI dependency that enforces the given policy for the current user.
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                request, session = _extract_request_and_session(func, args, kwargs)
                user_id = get_user_id_from_request(request)
                if session is not None:
                    if not await policy.check(user_id, session):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not have permission to access this resource.",
                        )
                    return await func(*args, **kwargs)

                granted = False
                async for db in get_session():
                    granted = await policy.check(user_id, db)
                if not granted:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You do not have permission to access this resource.",
                    )
                return await func(*args, **kwargs)

            return wrapper
        
        return decorator

    @staticmethod
    def required_all(*policies: Policy) -> Callable:
        """
        FastAPI dependency that enforces all given policies for the current user.
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                request, session = _extract_request_and_session(func, args, kwargs)
                user_id = get_user_id_from_request(request)
                if session is not None:
                    for policy in policies:
                        if not await policy.check(user_id, session):
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="You do not have permission to access this resource.",
                            )
                    return await func(*args, **kwargs)

                granted = False
                async for db in get_session():
                    granted = await PolicyEnforcer.check_all(user_id, list(policies), db)
                if not granted:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You do not have permission to access this resource.",
                    )
                return await func(*args, **kwargs)

            return wrapper
        
        return decorator

def _extract_request_and_session(
    func: Callable, 
    args: tuple, 
    kwargs: dict
) -> tuple:
    """
    Locate the ""Request" and "AsyncSession" parameters in the function's arguments.
    """
    request: Optional[Request] = kwargs.get("request")
    if request is None:
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request object not found in function arguments.",
        )

    session: Optional[AsyncSession] = kwargs.get("session")
    return request, session
