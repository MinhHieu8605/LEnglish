from datetime import time
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from app.utils.constants import SubtitleDisplay


class UserPreferencesUpdate(BaseModel):
    """
    Fields an authenticated user can change in their learning settings.

    Attributes:
        subtitle_display (Optional[SubtitleDisplay]): The subtitle languages or
            visibility setting.
        daily_goal_minutes (Optional[int]): The user's daily target for active study
            time in minutes.
        daily_new_words (Optional[int]): The user's daily target for newly learned
            words.
        reminder_enabled (Optional[bool]): Whether learning reminders are enabled.
        reminder_time (Optional[time]): The preferred local time for learning reminders,
            if configured.
        timezone (Optional[str]): The user's IANA timezone used for local dates and
            learning statistics.
    """

    subtitle_display: Optional[SubtitleDisplay] = None
    daily_goal_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    daily_new_words: Optional[int] = Field(default=None, ge=0, le=500)
    reminder_enabled: Optional[bool] = None
    reminder_time: Optional[time] = None
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate an optional timezone against the IANA timezone database.

        Args:
            value (Optional[str]): The optional IANA timezone name to validate.

        Returns:
            Optional[str]: The supplied timezone, or None when omitted.

        Raises:
            ValueError: If the timezone name is unknown.
        """
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Unknown IANA timezone") from exc
        return value


class UserPreferencesResponse(BaseModel):
    """
    Effective learning settings for the authenticated user.

    Attributes:
        id (Optional[int]): The unique identifier of the record.
        user_id (int): The identifier of the user who owns the record.
        subtitle_display (SubtitleDisplay): The subtitle languages or visibility
            setting.
        daily_goal_minutes (int): The user's daily target for active study time in
            minutes.
        daily_new_words (int): The user's daily target for newly learned words.
        reminder_enabled (bool): Whether learning reminders are enabled.
        reminder_time (Optional[time]): The preferred local time for learning reminders,
            if configured.
        timezone (str): The user's IANA timezone used for local dates and learning
            statistics.
    """

    model_config = {"from_attributes": True}

    id: Optional[int] = None
    user_id: int
    subtitle_display: SubtitleDisplay = SubtitleDisplay.BOTH
    daily_goal_minutes: int = 15
    daily_new_words: int = 5
    reminder_enabled: bool = True
    reminder_time: Optional[time] = None
    timezone: str = "Asia/Ho_Chi_Minh"
