from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import ReviewMode, ReviewScope, WordStatus


class ReviewProgress(Base, TimeStampMixin):
    """
    A user's spaced-repetition state for one vocabulary entry.

    Attributes:
        id (int): The unique identifier of the record.
        user_id (int): The identifier of the user who owns the record.
        vocabulary_id (int): The identifier of the associated vocabulary entry.
        status (str): The current learning or session state.
        ease_factor (Decimal): The multiplier used to calculate future successful-review
            intervals.
        repetition_count (int): The number of successful repetitions in the current
            review state.
        interval_days (int): The scheduled review interval in whole days.
        next_review_at (Optional[datetime]): The timestamp when the next review becomes
            due.
        last_reviewed_at (Optional[datetime]): The timestamp of the most recent recorded
            review, if any.
        personal_note (Optional[str]): The user's personal vocabulary note.
        user (User): The user account that owns the record.
        vocabulary (Vocabulary): The vocabulary entry associated with the record.
        attempts (List[ReviewAttempt]): The attempts recorded against this review
            progress.
    """

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
    vocabulary = relationship("Vocabulary", back_populates="review_progress_entries")
    attempts = relationship(
        "ReviewAttempt",
        back_populates="review_progress",
        cascade="all, delete-orphan",
    )


class ReviewAttempt(Base, TimeStampMixin):
    """
    One submitted vocabulary review attempt.

    Attributes:
        id (int): The unique identifier of the record.
        review_progress_id (int): The identifier of the review progress updated by this
            attempt.
        attempt_id (Optional[str]): The client-provided identifier used to deduplicate
            the review attempt.
        mode (Optional[str]): The practice mode used for this review attempt.
        correct (Optional[bool]): Whether the submitted answer was correct, if recorded.
        used_hint (bool): Whether the user requested a hint during the attempt.
        revealed_answer (bool): Whether the correct answer was shown before submission.
        submitted_answer (Optional[str]): The answer text recorded with the attempt, if
            supplied.
        rating (str): The user's selected recall rating.
        response_ms (Optional[int]): The time taken to answer in milliseconds, if
            supplied.
        reviewed_at (datetime): The timestamp when the review was recorded.
        review_progress (ReviewProgress): The user's review state associated with the
            attempt.
    """

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
    """
    A snapshot of one user's vocabulary review queue.

    Attributes:
        id (int): The unique identifier of the record.
        user_id (int): The identifier of the user who owns the record.
        topic_id (int): The identifier of the vocabulary topic being reviewed.
        scope (str): Whether the review session includes due words or all words.
        initial_mode (str): The practice mode selected when the session starts.
        status (str): The current learning or session state.
        current_position (int): The current position in the ordered review queue.
        total_items (int): The number of words included in the session.
        started_at (datetime): The timestamp when the session started.
        completed_at (Optional[datetime]): The completion timestamp, or None while
            unfinished.
        user (User): The user account that owns the record.
        topic (VocabularyTopic): The topic associated with the lesson or review session.
        items (List[ReviewSessionItem]): The entries belonging to this collection or
            session.
    """

    __tablename__ = "ReviewSession"
    __table_args__ = (Index("review_sessions_user_status_idx", "user_id", "status"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(
        Integer, ForeignKey("VocabularyTopic.id", ondelete="CASCADE"), nullable=False
    )
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
    """
    One vocabulary entry in a fixed review session.

    Attributes:
        id (int): The unique identifier of the record.
        session_id (int): The identifier of the review session containing the item.
        vocabulary_id (int): The identifier of the associated vocabulary entry.
        order_num (int): The position of the word or topic in the ordered collection.
        completed_at (Optional[datetime]): The completion timestamp, or None while
            unfinished.
        last_attempt_id (Optional[str]): The identifier of the item's most recent
            attempt, if any.
        session (ReviewSession): The session associated with this review queue item.
        vocabulary (Vocabulary): The vocabulary entry associated with the record.
    """

    __tablename__ = "ReviewSessionItem"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "vocabulary_id", name="uq_review_session_items_session_vocab"
        ),
        UniqueConstraint(
            "session_id", "order_num", name="uq_review_session_items_session_order"
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    session_id = Column(
        Integer, ForeignKey("ReviewSession.id", ondelete="CASCADE"), nullable=False
    )
    vocabulary_id = Column(
        Integer, ForeignKey("Vocabulary.id", ondelete="CASCADE"), nullable=False
    )
    order_num = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_attempt_id = Column(String, nullable=True)

    session = relationship("ReviewSession", back_populates="items")
    vocabulary = relationship("Vocabulary")
