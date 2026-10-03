from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin


class Notification(Base, TimeStampMixin):
    """
    Represents a user notification.

    Attributes:
        id (int): The unique identifier of the notification.
        user_id (int): The user identifier.
        type (str): Notification type (streak_reminder, review_due, etc.).
        title (str): Notification title.
        body (str): Notification body text.
        action_url (str): URL for notification action.
        metadata (dict): Additional metadata in JSON format.
        is_read (bool): Whether the notification has been read.
        read_at (datetime): When the notification was read.
    """
    __tablename__ = "Notification"
    __table_args__ = (Index("notifications_idx", "user_id", "is_read", "created_time"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text)
    action_url = Column(String)
    notification_metadata = Column("metadata", JSONB)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="notifications")
