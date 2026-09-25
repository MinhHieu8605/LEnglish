from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import PracticeScope, VocabularyDeckMode, WordStatus


class PracticeProgress(Base, TimeStampMixin):
    """A user's spaced-repetition state for one vocabulary entry."""

    __tablename__ = "PracticeProgress"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "vocabulary_id",
            name="uq_practice_progress_user_id_vocabulary_id",
        ),
        Index("practice_progress_idx", "user_id", "status", "next_review_at"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    vocabulary_id = Column(
        Integer, ForeignKey("Vocabulary.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(String, nullable=False, default=WordStatus.NEW.value)
    ease_factor = Column(Numeric(4, 2), nullable=False, default=2.50)
    repetition_count = Column(Integer, nullable=False, default=0)
    interval_days = Column(Integer, nullable=False, default=0)
    next_review_at = Column(DateTime(timezone=True))
    last_reviewed_at = Column(DateTime(timezone=True))
    personal_note = Column(Text)

    user = relationship("User", back_populates="practice_progress")
    vocabulary = relationship(
        "Vocabulary", back_populates="practice_progress_entries"
    )
    attempts = relationship(
        "PracticeAttempt",
        back_populates="practice_progress",
        cascade="all, delete-orphan",
    )


class PracticeAttempt(Base, TimeStampMixin):
    """One submitted vocabulary practice attempt and its review result."""

    __tablename__ = "PracticeAttempt"
    __table_args__ = (
        Index("practice_attempts_attempt_id_uq", "attempt_id", unique=True),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    practice_progress_id = Column(
        Integer, ForeignKey("PracticeProgress.id", ondelete="CASCADE"), nullable=False
    )
    attempt_id = Column(String, nullable=True)
    mode = Column(String, nullable=True)
    correct = Column(Boolean, nullable=True)
    used_hint = Column(Boolean, nullable=False, default=False)
    revealed_answer = Column(Boolean, nullable=False, default=False)
    submitted_answer = Column(Text, nullable=True)
    rating = Column(String, nullable=False)
    response_ms = Column(Integer)
    reviewed_at = Column(DateTime(timezone=True), nullable=False)

    practice_progress = relationship("PracticeProgress", back_populates="attempts")


class PracticeSession(Base, TimeStampMixin):
    """A snapshot of one user's vocabulary practice queue."""

    __tablename__ = "PracticeSession"
    __table_args__ = (Index("practice_sessions_user_status_idx", "user_id", "status"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("VocabularyTopic.id", ondelete="CASCADE"), nullable=False)
    scope = Column(String, nullable=False, default=PracticeScope.DUE.value)
    initial_mode = Column(String, nullable=False, default=VocabularyDeckMode.FLASHCARD.value)
    status = Column(String, nullable=False, default="started")
    current_position = Column(Integer, nullable=False, default=0)
    total_items = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="vocabulary_practice_sessions")
    topic = relationship("VocabularyTopic", back_populates="practice_sessions")
    items = relationship(
        "PracticeSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PracticeSessionItem.order_num",
    )


class PracticeSessionItem(Base, TimeStampMixin):
    """One vocabulary entry in a fixed practice-session queue."""

    __tablename__ = "PracticeSessionItem"
    __table_args__ = (
        UniqueConstraint("session_id", "vocabulary_id", name="uq_practice_session_items_session_vocab"),
        UniqueConstraint("session_id", "order_num", name="uq_practice_session_items_session_order"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    session_id = Column(Integer, ForeignKey("PracticeSession.id", ondelete="CASCADE"), nullable=False)
    vocabulary_id = Column(Integer, ForeignKey("Vocabulary.id", ondelete="CASCADE"), nullable=False)
    order_num = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_attempt_id = Column(String, nullable=True)

    session = relationship("PracticeSession", back_populates="items")
    vocabulary = relationship("Vocabulary")
