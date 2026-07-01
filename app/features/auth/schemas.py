from pydantic import BaseModel

from app.utils.constants import Role


class Login(BaseModel):
    """
    Schema for user login authentication.

    Attributes:
        email (str): User's email address.
        password (str): User's password.
    """
    email: str
    password: str


class Register(BaseModel):
    """
    Schema for new user registration.

    Attributes:
        email (str): User's email address.
        full_name (str): User's full name.
        password (str): User's password.
        role (Role): User's role (admin or user).
    """
    email: str
    full_name: str
    password: str
    role: Role
