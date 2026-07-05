from typing import Literal
from typing import Dict
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


class Login(BaseModel):
    """
    Schema for user login authentication.

    Attributes:
        email (Optional[str]): User's email address (for credentials login).
        password (Optional[str]): User's password (for credentials login).
        token_google (Optional[str]): Google OAuth 2.0 access token (for Google login).
    """
    email: Optional[str] = None
    password: Optional[str] = None
    token_google: Optional[str] = None


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

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, email):
        if isinstance(email, list):
            if len(email) > 0:
                email = email[0]
            else:
                raise ValueError("Email list cannot be empty")
        if not isinstance(email, str):
            raise ValueError("Email must be a string or a list containing a string")
        return email.lower()

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_fullname(cls, full_name):
        if isinstance(full_name, list):
            if len(full_name) > 0:
                full_name = full_name[0]
            else:
                raise ValueError("Full name list cannot be empty")
        if not isinstance(full_name, str):
            raise ValueError("Full name must be a string or a list containing a string")
        return full_name


class DefaultFilterModel(BaseModel):
    """
    Base model for filtering user data in API requests.

    Attributes:
        page (int): Page number for pagination. Defaults to 1.
        page_size (int): Number of items per page. Defaults to 10.
    """
    page: int = 1
    page_size: int = 10


class UserPaginationFilter(DefaultFilterModel):
    """
    Model for filtering and paginating user data.

    Attributes:
        role (Optional[str]): Filter by user's role.
        status (Optional[bool]): Filter by user's status.
        sorted_by (Optional[str]): Field to sort by.
        keyword (Optional[str]): Search keyword.
        sorted_order (Optional[str]): Order of sorting.
    """
    role: Optional[Role] = None
    status: Optional[bool] = None
    sorted_by: Optional[str] = None
    keyword: Optional[str] = Field(default=None, description="Search keyword", max_length=100)
    sorted_order: Optional[Literal["ascend", "descend"]] = "ascend"


class UserStatisticSummaryResponse(BaseModel):
    """
    Represents a paginated response for user data with statistical summary.
    """
    total_user: int
    user_by_role: Dict[str, int]
    number_active: int
    number_inactive: int


class ManagementResponseMetadata(BaseModel):
    """
    Metadata for user management response.
    
    Attributes:
        total (int): Total number of users.
        page (int): Current page number.
        page_size (int): Number of items per page.
        pages (int): Total number of pages.
    """
    total: int
    page: int
    page_size: int
    pages: int


class UserManagementItemResponse(BaseModel):
    """
    Represents a user in the user management response.
    
    Attributes:
        id (int): Unique identifier of the user.
        email (str): Email address of the user.
        full_name (str): Full name of the user.
        role: Role of the user.
        active (bool): Whether the user is active.
        created_time (Optional[datetime]): Timestamp when the user was created.
        lastest_login (Optional[datetime]): Timestamp of the user's last login.
        lastest_request (Optional[datetime]): Timestamp of the user's last request.
    """
    id: int
    email: str
    full_name: str
    role: str
    active: bool
    created_time: Optional[datetime] = None
    lastest_login: Optional[datetime] = None
    lastest_request: Optional[datetime] = None


class PaginatedUserListResponse(BaseModel):
    """
    Response model for paginated user list.
    
    Attributes:
        meta (ManagementResponseMetadata): Metadata for user management.
        data (List[UserManagementItemResponse]): List of user data.
    """
    data: List[UserManagementItemResponse]
    statistic_summary: UserStatisticSummaryResponse
    metadata: ManagementResponseMetadata
