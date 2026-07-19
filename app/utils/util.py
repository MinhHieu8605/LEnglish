from fastapi import HTTPException, status

from app.utils.constants import Message


def get_token_from_request(request):
    """
    Extracts the bearer token from the Authorization header in the request.

    Args:
        request (Request): The FastAPI request object.

    Returns:
        str: The token string if found, otherwise None.
    """
    token = None
    if "Token" in request.headers:
        token = request.headers["Token"]
    elif "Authorization" in request.headers:
        token = request.headers["Authorization"].split()[-1]
    return token


def check_user_id_match(user_id: int, request):
    """
    Checks if the user ID from the request matches the provided user ID.

    Args:
        user_id (int): The user ID to check against.
        request (Request): The FastAPI request object.
    """
    try:
        if int(request.state.user_id) != int(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Message.MSG_UNAUTHORIZED,
            )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID provided.",
        )
