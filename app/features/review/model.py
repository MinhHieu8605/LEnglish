from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import ReviewScope, ReviewMode, WordStatus


class ReviewProgress(Base, TimeStampMixin):
    """A user's spaced-repetition state for one vocabulary entry."""

    __tablename__ = "ReviewProgress"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "vocabulary_id",
            name="uq_review_progress_user_id_vocabulary_id",
        ),
        Index("review_progress_idx", "user_id", "status", "next_review_at"),
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

    user = relationship("User", back_populates="review_progress")
    vocabulary = relationship(
        "Vocabulary", back_populates="review_progress_entries"
    )
    attempts = relationship(
        "ReviewAttempt",
        back_populates="review_progress",
        cascade="all, delete-orphan",
    )


class ReviewAttempt(Base, TimeStampMixin):
    """One submitted vocabulary review attempt."""

    __tablename__ = "ReviewAttempt"
    __table_args__ = (
        Index("review_attempts_attempt_id_uq", "attempt_id", unique=True),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    review_progress_id = Column(
        Integer, ForeignKey("ReviewProgress.id", ondelete="CASCADE"), nullable=False
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

    review_progress = relationship("ReviewProgress", back_populates="attempts")


class ReviewSession(Base, TimeStampMixin):
    """A snapshot of one user's vocabulary review queue."""

    __tablename__ = "ReviewSession"
    __table_args__ = (Index("review_sessions_user_status_idx", "user_id", "status"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("VocabularyTopic.id", ondelete="CASCADE"), nullable=False)
    scope = Column(String, nullable=False, default=ReviewScope.DUE.value)
    initial_mode = Column(String, nullable=False, default=ReviewMode.FLASHCARD.value)
    status = Column(String, nullable=False, default="started")
    current_position = Column(Integer, nullable=False, default=0)
    total_items = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="review_sessions")
    topic = relationship("VocabularyTopic", back_populates="review_sessions")
    items = relationship(
        "ReviewSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ReviewSessionItem.order_num",
    )


class ReviewSessionItem(Base, TimeStampMixin):
    """One vocabulary entry in a fixed review session."""

    __tablename__ = "ReviewSessionItem"
    __table_args__ = (
        UniqueConstraint("session_id", "vocabulary_id", name="uq_review_session_items_session_vocab"),
        UniqueConstraint("session_id", "order_num", name="uq_review_session_items_session_order"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    session_id = Column(Integer, ForeignKey("ReviewSession.id", ondelete="CASCADE"), nullable=False)
    vocabulary_id = Column(Integer, ForeignKey("Vocabulary.id", ondelete="CASCADE"), nullable=False)
    order_num = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_attempt_id = Column(String, nullable=True)

    session = relationship("ReviewSession", back_populates="items")
    vocabulary = relationship("Vocabulary")
