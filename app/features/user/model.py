from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.middleware.security import get_password_hash, verify_password
from app.utils.constants import Role


class User(Base, TimeStampMixin):
    """
    Represents a user account in the system.

    Attributes:
        id (int): The unique identifier of the user.
        email (str): The unique email address of the user.
        password (str): The hashed password of the user.
        full_name (str): The full name of the user.
        avatar_url (str): The avatar URL of the user.
        lastest_login (datetime): The timestamp of the user's last login.
        lastest_request (datetime): The timestamp of the user's last request.
        deleted (bool): Indicates whether the user has been deleted.
    """

    __tablename__ = "User"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)
    id = Column(Integer, autoincrement=True, primary_key=True)
    email = Column(UnicodeText, nullable=False)
    password = Column(String, default="")
    full_name = Column(String)
    avatar_url = Column(String)
    lastest_login = Column(DateTime(timezone=True), nullable=True, default=None)
    lastest_request = Column(DateTime(timezone=True), nullable=True, default=None)
    deleted = Column(Boolean, nullable=False, default=False)

    def check_password(self, password: str):
        """
        Checks whether the given password matches the user's stored password.

        Args:
            password (str): The plain-text password to verify.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return verify_password(password, self.password)

    def change_password(self, password: str):
        """
        Changes the user's password to the given password.

        Args:
            password (str): The new plain-text password to set.
        """
        self.password = get_password_hash(password)

    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    roles = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    preferences = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    lesson_progress = relationship(
        "LessonProgress", back_populates="user", cascade="all, delete-orphan"
    )
    lesson_sessions = relationship(
        "LessonSession", back_populates="user", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    word_lists = relationship(
        "WordList", back_populates="user", cascade="all, delete-orphan"
    )
    review_progress = relationship(
        "ReviewProgress", back_populates="user", cascade="all, delete-orphan"
    )
    review_sessions = relationship(
        "ReviewSession", back_populates="user", cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )


class UserRole(Base, TimeStampMixin):
    """
    Represents a role assigned to a user account.

    Attributes:
        id (int): The unique identifier of the user role.
        email (str): The email address of the related user.
        role (str): The role assigned to the user.
    """

    __tablename__ = "UserRole"
    __table_args__ = (
        UniqueConstraint("email", "role", name="uq_user_roles_email_role"),
    )
    id = Column(Integer, autoincrement=True, primary_key=True)
    email = Column(
        UnicodeText, ForeignKey("User.email", ondelete="CASCADE"), nullable=False
    )
    role = Column(String, nullable=False, default=Role.USER.value)

    user = relationship("User", back_populates="roles")
