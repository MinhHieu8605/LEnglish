from typing import Any, Literal, Optional, overload

from fastapi import HTTPException, Request,status
from pydantic import BaseModel

from loguru import logger


def raise_not_found(message: str = "record not found"):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

def raise_bad_request(message: str = "Bad request"):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

def page_size_to_offset_limit(page: int, page_size: int):
    """
    Calculate offset and limit from page and page size

    Args:
        page (int): The page number (1-based index).
        page_size (int): The number of items per page.

    Returns:
        tuple: A tuple containing the offset and limit.
    """
    return (page - 1) * page_size, page_size

def get_nested_value(obj, attr_path, default=None) -> Any:
    """
    Retrieve a nested value from a dictionary or object using a dot-separated attribute path.

    Args:
        obj (dict or object): The dictionary or object to retrieve the value from.
        attr_path (str): The dot-separated attribute path (e.g., "a.b.c").
        default: The default value to return if the attribute path does not exist.
    
    Returns:
        The value at the specified attribute path, or the default value if the path does not exist.
    
    Example:
        >>> data = {'user': {'name': 'Alice', 'age': 30}}
        >>> get_nested_value(data, "user.name")
        'Alice'
        >>> get_nested_value(data, 'user.email', default='Not found')
        'Not found'
    """
    

    def _get_attr(obj, attr):
        if isinstance(obj, dict):
            return obj.get(attr)
        elif isinstance(obj, BaseModel):
            return getattr(obj, attr, None)
        return getattr(obj, attr, None)

    try:
        for attr in attr_path.split('.'):
            obj = _get_attr(obj, attr)
            if obj is None:
                return default
        return obj
    except (KeyError, AttributeError) as e:
        logger.error(f"Error retrieving nested value for path '{attr_path}': {e}")
        return default


@overload
def get_user_id_from_request(
    request: Request,
    raise_if_missing: Literal[True] = ...
) -> int: ...


@overload
def get_user_id_from_request(
    request: Request,
    raise_if_missing: Literal[False]
) -> Optional[int]: ...


def get_user_id_from_request(
    request: Request,
    raise_if_missing: bool = True
) -> Optional[int]:
    """
    Extract the user ID from the request state.
    """
    user_id = get_nested_value(request, "state.user_id")
    if user_id is None and raise_if_missing:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID not found in request state"
        )
    return user_id


@overload
def get_user_email_from_request(
    request: Request,
    raise_if_missing: Literal[True] = ...
) -> str: ...


@overload
def get_user_email_from_request(
    request: Request,
    raise_if_missing: Literal[False]
) -> Optional[str]: ...


def get_user_email_from_request(
    request: Request,
    raise_if_missing: bool = True
) -> Optional[str]:
    """
    Extract the user email from the request state.
    """
    email = get_nested_value(request, "state.email")
    if email is None and raise_if_missing:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User email not found in request state"
        )
    return email


@overload
def get_user_role_from_request(
    request: Request,
    raise_if_missing: Literal[True] = ...
) -> str: ...


@overload
def get_user_role_from_request(
    request: Request,
    raise_if_missing: Literal[False]
) -> Optional[str]: ...


def get_user_role_from_request(
    request: Request,
    raise_if_missing: bool = True
) -> Optional[str]:
    """
    Extract the user role from the request state.
    """
    role = get_nested_value(request, "state.role")
    if role is None and raise_if_missing:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User role not found in request state"
        )
    return role
