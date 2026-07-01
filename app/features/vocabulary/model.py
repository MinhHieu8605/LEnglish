from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import WordStatus, WordType


class Vocabulary(Base, TimeStampMixin):
    """
    Represents a vocabulary word or phrase.

    Attributes:
        id (int): The unique identifier of the vocabulary.
        word (str): The original word or phrase.
        normalized_word (str): Normalized form for searching.
        word_type (str): Type of word (noun, verb, adjective, etc.).
        ipa (str): International Phonetic Alphabet pronunciation.
        audio_url (str): URL to pronunciation audio.
        image_url (str): URL to illustrative image.
        definition_vi (str): Vietnamese definition.
        definition_en (str): English definition.
        example_sentence (str): Example sentence using the word.
        example_translation_vi (str): Vietnamese translation of example.
        source_subtitle_id (int): Source subtitle where word was found.
    """
    __tablename__ = "vocabularies"
    __table_args__ = (UniqueConstraint("normalized_word", "word_type", name="uq_vocabularies_normalized_word_word_type"),)

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    word = Column(String, nullable=False)
    normalized_word = Column(String, nullable=False, index=True)
    word_type = Column(String, nullable=False, default=WordType.OTHER.value)
    ipa = Column(String)
    audio_url = Column(String)
    image_url = Column(String)
    definition_vi = Column(Text, nullable=False)
    definition_en = Column(Text)
    example_sentence = Column(Text)
    example_translation_vi = Column(Text)
    source_subtitle_id = Column(Integer, ForeignKey("subtitles.id", ondelete="SET NULL"), nullable=True)

    source_subtitle = relationship("Subtitle", back_populates="vocabulary_items")
    notebook_entries = relationship("NotebookEntry", back_populates="vocabulary", cascade="all, delete-orphan")
    progress_entries = relationship("VocabularyProgress", back_populates="vocabulary", cascade="all, delete-orphan")

class Notebook(Base, TimeStampMixin):
    """
    Represents a user's vocabulary notebook collection.

    Attributes:
        id (int): The unique identifier of the notebook.
        user_id (int): The user identifier.
        name (str): The notebook name.
        description (str): The notebook description.
        is_default (bool): Whether this is the default notebook.
    """
    __tablename__ = "notebooks"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_notebooks_user_id_name"),
        Index("ix_notebooks_one_default_per_user", "user_id", unique=True, postgresql_where=text("is_default = true")),
    )

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    is_default = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="notebooks")
    entries = relationship("NotebookEntry", back_populates="notebook", cascade="all, delete-orphan")


class NotebookEntry(Base, TimeStampMixin):
    """
    Represents a vocabulary entry in a notebook.

    Attributes:
        id (int): The unique identifier of the notebook entry.
        notebook_id (int): The notebook identifier.
        vocabulary_id (int): The vocabulary identifier.
        context_sentence (str): Context sentence for this entry.
        note (str): User's personal note.
        added_at (datetime): When the entry was added.
    """
    __tablename__ = "notebook_entries"
    __table_args__ = (UniqueConstraint("notebook_id", "vocabulary_id", name="uq_notebook_entries_notebook_id_vocabulary_id"),)

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id", ondelete="CASCADE"), nullable=False)
    context_sentence = Column(Text)
    note = Column(Text)
    added_at = Column(DateTime(timezone=True), nullable=False)

    notebook = relationship("Notebook", back_populates="entries")
    vocabulary = relationship("Vocabulary", back_populates="notebook_entries")


class VocabularyProgress(Base, TimeStampMixin):
    """
    Represents a user's learning progress for a vocabulary word using spaced repetition.

    Attributes:
        id (int): The unique identifier of the vocabulary progress.
        user_id (int): The user identifier.
        vocabulary_id (int): The vocabulary identifier.
        status (str): Learning status (learning, reviewing, mastered, ignored).
        ease_factor (Decimal): Spaced repetition ease factor.
        repetition_count (int): Number of times reviewed.
        interval_days (int): Days until next review.
        next_review_at (datetime): Next scheduled review time.
        last_reviewed_at (datetime): Last review time.
        personal_note (str): User's personal note.
    """
    __tablename__ = "vocabulary_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "vocabulary_id", name="uq_vocabulary_progress_user_id_vocabulary_id"),
        Index("ix_vocabulary_progress_user_id_status_next_review_at", "user_id", "status", "next_review_at"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default=WordStatus.LEARNING.value)
    ease_factor = Column(Numeric(4, 2), nullable=False, default=2.50)
    repetition_count = Column(Integer, nullable=False, default=0)
    interval_days = Column(Integer, nullable=False, default=0)
    next_review_at = Column(DateTime(timezone=True))
    last_reviewed_at = Column(DateTime(timezone=True))
    personal_note = Column(Text)

    user = relationship("User", back_populates="vocabulary_progress")
    vocabulary = relationship("Vocabulary", back_populates="progress_entries")
    review_logs = relationship("VocabularyReviewLog", back_populates="vocabulary_progress", cascade="all, delete-orphan")


class VocabularyReviewLog(Base, TimeStampMixin):
    """
    Represents a review log entry for vocabulary spaced repetition.

    Attributes:
        id (int): The unique identifier of the review log.
        vocabulary_progress_id (int): The vocabulary progress identifier.
        rating (str): Review rating (again, hard, good, easy).
        response_ms (int): Response time in milliseconds.
        reviewed_at (datetime): When the review happened.
    """
    __tablename__ = "vocabulary_review_logs"
    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    vocabulary_progress_id = Column(Integer, ForeignKey("vocabulary_progress.id", ondelete="CASCADE"), nullable=False)
    rating = Column(String, nullable=False)
    response_ms = Column(Integer)
    reviewed_at = Column(DateTime(timezone=True), nullable=False)

    vocabulary_progress = relationship("VocabularyProgress", back_populates="review_logs")
