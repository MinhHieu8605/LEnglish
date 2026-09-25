from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import LessonSessionMode, LessonSessionStatus


class LessonProgress(Base, TimeStampMixin):
    """
    Represents a user's progress through a lesson.

    Attributes:
        id (int): The unique identifier of the learning progress.
        user_id (int): The user identifier.
        lesson_id (int): The lesson identifier.
        last_position_seconds (int): Last watched position in seconds.
        completion_percent (Decimal): Completion percentage (0-100).
        completed_at (datetime): When the lesson was completed.
        last_watched_at (datetime): Last time the lesson was watched.
    """
    __tablename__ = "LessonProgress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_id_lesson_id"),
        CheckConstraint("completion_percent >= 0 AND completion_percent <= 100", name="completion_percent_range"),
        Index("lesson_progress_idx", "user_id", "last_watched_at"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=False)
    last_position_seconds = Column(Integer, nullable=False, default=0)
    completion_percent = Column(Numeric(5, 2), nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True))
    last_watched_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="lesson_progress")


class LessonSession(Base, TimeStampMixin):
    """
    Represents a practice session for a lesson.

    Attributes:
        id (int): The unique identifier of the practice session.
        user_id (int): The user identifier.
        lesson_id (int): The lesson identifier.
        mode (str): Practice mode (dictation, listening, shadowing, quiz).
        status (str): Session status (started, completed, abandoned).
        score (Decimal): Overall score percentage.
        correct_count (int): Number of correct answers.
        total_count (int): Total number of questions.
        duration_seconds (int): Session duration in seconds.
        started_at (datetime): When the session started.
        completed_at (datetime): When the session completed.
    """
    __tablename__ = "LessonSession"
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=False)
    mode = Column(String, nullable=False, default=LessonSessionMode.DICTATION.value)
    status = Column(String, nullable=False, default=LessonSessionStatus.STARTED.value)
    score = Column(Numeric(5, 2))
    correct_count = Column(Integer, nullable=False, default=0)
    total_count = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="lesson_sessions")
    lesson = relationship("Lesson", back_populates="lesson_sessions")
    answers = relationship("LessonAnswer", back_populates="session", cascade="all, delete-orphan")


class LessonAnswer(Base, TimeStampMixin):
    """
    Represents a user's answer in a practice session.

    Attributes:
        id (int): The unique identifier of the practice answer.
        session_id (int): The practice session identifier.
        subtitle_id (int): The subtitle identifier.
        user_input (str): User's answer input.
        accuracy_score (Decimal): Accuracy score percentage.
        is_correct (bool): Whether the answer is correct.
        attempt_count (int): Number of attempts for this question.
        answered_at (datetime): When the answer was submitted.
    """
    __tablename__ = "LessonAnswer"
    __table_args__ = (UniqueConstraint("session_id", "subtitle_id", name="uq_lesson_answers_session_id_subtitle_id"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    session_id = Column(Integer, ForeignKey("LessonSession.id", ondelete="CASCADE"), nullable=False)
    subtitle_id = Column(Integer, ForeignKey("Subtitle.id", ondelete="CASCADE"), nullable=False)
    user_input = Column(Text, nullable=False)
    accuracy_score = Column(Numeric(5, 2))
    is_correct = Column(Boolean, nullable=False, default=False)
    attempt_count = Column(Integer, nullable=False, default=1)
    answered_at = Column(DateTime(timezone=True), nullable=False)

    session = relationship("LessonSession", back_populates="answers")
    subtitle = relationship("Subtitle", back_populates="lesson_answers")
