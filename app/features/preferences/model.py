from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import SubtitleDisplay


class UserPreferences(Base, TimeStampMixin):
    """
    Represents user settings and preferences.

    Attributes:
        id (int): The unique identifier of the user preferences.
        user_id (int): The unique identifier of the related user.
        subtitle_display (str): Subtitle display preference.
        daily_goal_minutes (int): Daily study goal in minutes.
        daily_new_words (int): Daily new words goal.
        reminder_enabled (bool): Whether reminders are enabled.
        reminder_time (time): Time for daily reminders.
        timezone (str): User's timezone.
    """
    __tablename__ = "user_preferences"
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    subtitle_display = Column(String, nullable=False, default=SubtitleDisplay.BOTH.value)
    daily_goal_minutes = Column(Integer, nullable=False, default=15)
    daily_new_words = Column(Integer, nullable=False, default=5)
    reminder_enabled = Column(Boolean, nullable=False, default=True)
    reminder_time = Column(Time)
    timezone = Column(String, nullable=False, default="Asia/Ho_Chi_Minh")

    user = relationship("User", back_populates="preferences")
