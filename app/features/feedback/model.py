from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import FeedbackStatus

if TYPE_CHECKING:
    from app.features.user.model import User

DEFAULT_FEEDBACK_STATUS = FeedbackStatus.NEW.value


class Feedback(Base, TimeStampMixin):
    """
    Represents user feedback in the system.

    Inherits from:
        Base: The base class for SQLAlchemy models.
        TimeStampMixin: A mixin that adds created_at and updated_at timestamp columns.

    Attributes:
        id (int): The unique identifier of the feedback.
        user_id (int): The ID of the user who submitted the feedback.
        type (str): The type of feedback (e.g., bug report, feature request).
        title (str): The title of the feedback.
        description (str): A detailed description of the feedback.
    """

    __tablename__ = "Feedback"
    __table_args__ = (
        Index("feedback_idx", "user_id", "type", postgresql_using="btree"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    status: Mapped[FeedbackStatus] = mapped_column(
        String(50), nullable=False, default=DEFAULT_FEEDBACK_STATUS
    )
    user_attachments: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True, server_default=text("'{}'::text[]")
    )
    response: Mapped[Optional[str]] = mapped_column(String(3000), nullable=True)
    response_attachments: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True, server_default=text("'{}'::text[]")
    )
    response_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    user: Mapped["User"] = relationship(lazy="noload")

    def __repr__(self) -> str:
        """
        Represent feedback with its identifier, owner, and status.

        Returns:
            str: A concise representation of the feedback record.
        """
        return (
            f"Feedback(id={self.id!r}, user_id={self.user_id!r}, "
            f"status={self.status!r})"
        )


class FeedbackAttachment(Base):
    """
    Represents attachments associated with user feedback.

    Inherits from:
        Base: The base class for SQLAlchemy models.

    Attributes:
        id (int): The unique identifier of the attachment.
        feedback_id (int): The ID of the feedback to which the attachment belongs.
        file_path (str): The file path or URL of the attachment.
    """

    __tablename__ = "FeedbackAttachment"
    __table_args__ = (
        Index("feedback_attachment_idx", "feedback_id", postgresql_using="btree"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feedback_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Feedback.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    attachment_type: Mapped[str] = mapped_column(String(50), nullable=False)
