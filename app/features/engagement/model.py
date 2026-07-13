from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.database.model import Base, TimeStampMixin


class ActivityEvent(Base, TimeStampMixin):
    """
    Represents a user activity event for tracking and engagement.

    Attributes:
        id (int): The unique identifier of the activity event.
        user_id (int): The user identifier.
        type (str): Activity type (lesson_viewed, practice_completed, etc.).
        lesson_id (int): Related lesson identifier (optional).
        vocabulary_id (int): Related vocabulary identifier (optional).
        practice_session_id (int): Related practice session identifier (optional).
        conversation_id (int): Related conversation identifier (optional).
        duration_seconds (int): Activity duration in seconds.
        xp_earned (int): Experience points earned.
        metadata (dict): Additional metadata in JSON format.
    """
    __tablename__ = "activity_events"
    __table_args__ = (
        Index("ix_activity_events_user_id_created_time", "user_id", "created_time"),
        Index("ix_activity_events_user_id_type_created_time", "user_id", "type", "created_time"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id", ondelete="SET NULL"), nullable=True)
    practice_session_id = Column(Integer, ForeignKey("practice_sessions.id", ondelete="SET NULL"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    duration_seconds = Column(Integer, nullable=False, default=0)
    xp_earned = Column(Integer, nullable=False, default=0)
    event_metadata = Column("metadata", JSONB)

    user = relationship("User")
    lesson = relationship("Lesson")
    vocabulary = relationship("Vocabulary")
    practice_session = relationship("PracticeSession")
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
    __tablename__ = "achievements"
    id = Column(Integer, autoincrement=True, primary_key=True)
    code = Column(String, nullable=False, unique=True)
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
    __tablename__ = "achievement_unlocks"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_achievement_unlocks_user_id_achievement_id"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False)
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
    __tablename__ = "streaks"
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    last_active_date = Column(Date)

    user = relationship("User")
