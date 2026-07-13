import time
from fastapi import HTTPException, status
from jose import JWTError, jwt

from passlib.context import CryptContext

from app.config.settings import JWT

access_token_jwt_subject = "access_token"
jwt_config = JWT()


def get_password_hash(password):
    """
    Generates a bcrypt hash of the given password.

    Args:
        password (str): The password to hash.

    Returns:
        str: The bcrypt hash of the password.
    """
    return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)

def verify_password(plain_password, hashed_password):
    """
    Verifies a plain password against a stored bcrypt hash.

    Args:
        plain_password (str): The plain-text password to check.
        hashed_password (str): The stored bcrypt hash to verify against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return CryptContext(schemes=["bcrypt"], deprecated="auto").verify(plain_password, hashed_password)


# =============================================================================
# TOKEN GENERATION
# =============================================================================


def create_access_token(*, data: dict):
    """
    Creates an access token.

    Args:
        data (dict): The data to include in the token payload.

    Returns:
        str: The encoded JWT access token.
    """
    rt = int(time.time())
    to_encode = data.copy()
    expire = int(jwt_config.access_token_expire_minutes or 60) * 60
    to_encode.update(
        {
            "rt": rt,
            "expire_after": expire,
            "sub": access_token_jwt_subject,
        }
    )
    encoded_jwt = jwt.encode(
        to_encode,
        str(jwt_config.jwt_secret_key),
        algorithm=jwt_config.jwt_alg,
    )
    return encoded_jwt


def create_refresh_token(uid: int, email: str) -> str:
    """
    Creates a refresh token.

    Args:
        uid (str): The user ID.
        email (str): The user's email address.

    Returns:
        str: The encoded refresh token.
    """
    rt = int(time.time())
    expire = int(jwt_config.refresh_token_expire_minutes or 1440) * 60
    token = jwt.encode(
        {
            "rt": rt,
            "expire_after": expire,
            "uid": uid,
            "email": email,
            "token_type": "refresh",
        },
        str(jwt_config.jwt_secret_key),
        algorithm=jwt_config.jwt_alg,
    )
    return token


# =============================================================================
# TOKEN VALIDATION
# =============================================================================


def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token.

    Args:
        token (str): The JWT token to verify.

    Returns:
        dict: The decoded token payload.

    Raises:
        JWTError: If the token is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            jwt_config.jwt_secret_key,
            algorithms=jwt_config.jwt_alg,
        )
        return payload
    except JWTError:
        raise JWTError("Invalid token")


def validate_token(token: str) -> tuple[bool, dict]:
    """
    Validates a JWT token and extracts user information.

    Args:
        token (str): The JWT token to validate.

    Returns:
        tuple: A tuple containing a boolean indicating if the token is
            valid, and a dictionary with the decoded token information.

    Raises:
        HTTPException: If the token is invalid or cannot be decoded.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    rt = int(time.time())
    token_raw = None
    try:
        token_raw = verify_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    tk_rt = token_raw["rt"]
    tk_ex = token_raw["expire_after"]

    # Validate time expired token
    if tk_rt <= rt and (rt - tk_rt) <= int(tk_ex):
        return True, token_raw
    else:
        # Token is outdated
        return False, token_raw
