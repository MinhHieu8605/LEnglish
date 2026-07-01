from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.constants import Role


class UserCreate(BaseModel):
    """
    Schema for creating new user accounts (supports batch creation).

    Attributes:
        email (List[EmailStr]): One or more email addresses for account creation (1-5).
        full_name (List[str]): One or more full names corresponding to emails (1-5).
        password (Optional[str]): Password for new users. Must be at least 8 characters.
        role (Role): Role assigned to the users. Defaults to USER.
    """
    model_config = {
        "json_schemas_extra": {
            "example": {
                "email": ["test@example.com"],
                "full_name": ["Minh Hiếu"],
                "password": "securepassword",
                "role": "user",
            }
        }
    }
    email: List[EmailStr] = Field(
        min_length=1,
        max_length=5,
        description=(
            "One or more email address to create account"
        )
    )
    full_name: List[str] = Field(
        min_length=1,
        max_length=5,
        description=(
            "One or more full name to create account"
        )
    )
    password: Optional[str] = Field(
        default=None,
        description="Password for new user. Must 8 characters"
    )
    role: Role = Field(
        default=Role.USER,
        description="Top-level role assigned to the user."
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email_list(cls, email):
        if isinstance(email, str):
            email = [email]
        if not isinstance(email, list):
            raise ValueError("Must be a list of email addresses")
        return [e.lower() if isinstance(e, str) else e for e in email]
    
    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, password):
        if password is not None and len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        return password


class UserUpdate(BaseModel):
    """
    Schema for updating existing user information.

    Attributes:
        full_name (Optional[str]): Updated full name of the user.
        role (Optional[Role]): Updated role assignment for the user.
        password (Optional[str]): Updated password. Must be at least 8 characters if provided.
    """
    model_config = {
        "json_schemas_extra": {
            "example": {
                "full_name": "Nguyễn Văn A",
                "role": "user",
                "password": "newpassword123"
            }
        }
    }
    full_name: Optional[str] = Field(
        default=None,
        description="Updated full name of the user"
    )
    role: Optional[Role] = Field(
        default=None,
        description="Updated role for the user"
    )
    password: Optional[str] = Field(
        default=None,
        description="Updated password. Must be at least 8 characters"
    )
    deleted: Optional[bool]

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, password):
        if password is not None and len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        return password


class UserResponse(BaseModel):
    """
    Schema for user data in API responses.

    Attributes:
        id (int): Unique identifier of the user.
        email (EmailStr): User's email address.
        full_name (str): User's full name.
        avatar_url (Optional[str]): URL to user's avatar image.
        deleted (bool): Whether the user account is deleted.
        created_time (Optional[datetime]): Timestamp when the user was created.
        updated_time (Optional[datetime]): Timestamp when the user was last updated.
    """
    model_config = {
        "from_attributes": True,
        "json_schemas_extra": {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "Minh Hiếu",
                "avatar_url": "https://example.com/avatar.jpg",
                "role": "user",
                "deleted": False,
                "created_time": "2024-01-01T00:00:00Z",
                "updated_time": "2024-01-01T00:00:00Z"
            }
        }
    }
    id: int
    email: EmailStr
    full_name: str
    avatar_url: Optional[str]
    role: Role
    deleted: bool
    created_time: Optional[datetime]
    updated_time: Optional[datetime]
