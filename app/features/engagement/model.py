from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin


class ActivityEvent(Base, TimeStampMixin):
    """
    Represents a user activity event for tracking and engagement.

    Attributes:
        id (int): The unique identifier of the activity event.
        user_id (int): The user identifier.
        type (str): Activity type (listening, vocabulary, lesson_viewed, etc.).
        event_id (str): Optional identifier for deduplicating reported activity.
        lesson_id (int): Related lesson identifier (optional).
        vocabulary_id (int): Related vocabulary identifier (optional).
        lesson_session_id (int): Related lesson session identifier (optional).
        conversation_id (int): Related conversation identifier (optional).
        duration_seconds (int): Activity duration in seconds.
        xp_earned (int): Experience points earned.
        metadata (dict): Additional metadata in JSON format.
    """

    __tablename__ = "ActivityEvent"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_activity_events_user_event"),
        Index("activity_events_idx", "user_id", "created_time"),
        Index("activity_events_type_idx", "user_id", "type", "created_time"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    event_id = Column(String(36), nullable=True)
    lesson_id = Column(
        Integer, ForeignKey("Lesson.id", ondelete="SET NULL"), nullable=True
    )
    vocabulary_id = Column(
        Integer, ForeignKey("Vocabulary.id", ondelete="SET NULL"), nullable=True
    )
    lesson_session_id = Column(
        Integer, ForeignKey("LessonSession.id", ondelete="SET NULL"), nullable=True
    )
    conversation_id = Column(
        Integer, ForeignKey("Conversation.id", ondelete="SET NULL"), nullable=True
    )
    duration_seconds = Column(Integer, nullable=False, default=0)
    xp_earned = Column(Integer, nullable=False, default=0)
    event_metadata = Column("metadata", JSONB)

    user = relationship("User")
    lesson = relationship("Lesson")
    vocabulary = relationship("Vocabulary")
    lesson_session = relationship("LessonSession")
    conversation = relationship("Conversation")


class Achievement(Base, TimeStampMixin):
    """
    Represents an achievement that users can unlock.

    Attributes:
        id (int): The unique identifier of the achievement.
        code (str): Unique achievement code.
        name (str): Achievement name.
        description (str): Achievement description.
        icon_url (str): Icon image URL.
        condition_type (str): Type of condition to unlock.
        condition_value (int): Value required to unlock.
        xp_reward (int): Experience points reward.
        display_order (int): Display order for sorting.
    """

    __tablename__ = "Achievement"
    __table_args__ = (UniqueConstraint("code", name="uq_achievements_code"),)
    id = Column(Integer, autoincrement=True, primary_key=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    icon_url = Column(String)
    condition_type = Column(String, nullable=False)
    condition_value = Column(Integer, nullable=False, default=1)
    xp_reward = Column(Integer, nullable=False, default=0)
    display_order = Column(Integer, nullable=False, default=0)


class AchievementUnlock(Base, TimeStampMixin):
    """
    Represents a user unlocking an achievement.

    Attributes:
        id (int): The unique identifier of the unlock record.
        user_id (int): The user identifier.
        achievement_id (int): The achievement identifier.
        earned_at (datetime): When the achievement was earned.
    """

    __tablename__ = "AchievementUnlock"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "achievement_id",
            name="uq_achievement_unlocks_user_id_achievement_id",
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(
        Integer, ForeignKey("Achievement.id", ondelete="CASCADE"), nullable=False
    )
    earned_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User")
    achievement = relationship("Achievement")


class Streak(Base, TimeStampMixin):
    """
    Represents user's learning streak information.

    Attributes:
        id (int): The unique identifier of the streak record.
        user_id (int): The unique identifier of the related user.
        current_streak (int): Current consecutive days streak.
        longest_streak (int): Longest streak ever achieved.
        last_active_date (date): Last date user was active.
    """

    __tablename__ = "Streak"
    __table_args__ = (UniqueConstraint("user_id", name="uq_streaks_user_id"),)
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    last_active_date = Column(Date)

    user = relationship("User")
