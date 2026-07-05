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
    