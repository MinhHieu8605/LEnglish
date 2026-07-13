import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import VocabularyBookCategory, WordStatus, WordType


class Vocabulary(Base, TimeStampMixin):
    """
    Represents a vocabulary word or phrase.

    Attributes:
        id (int): The unique identifier of the vocabulary.
        word (str): The original word or phrase.
        word_type (str): Type of word (noun, verb, adjective, etc.).
        ipa (str): International Phonetic Alphabet pronunciation.
        audio_url (str): URL to pronunciation audio.
        image_url (str): URL to illustrative image.
        definition_vi (str): Vietnamese definition.
        example_sentence (str): Example sentence using the word.
        example_translation_vi (str): Vietnamese translation of example.
        source_subtitle_id (int): Source subtitle where word was found.
    """
    __tablename__ = "vocabularies"
    __table_args__ = (
        Index("uq_vocabularies_word_word_type", sa.literal_column("lower(word)"), "word_type", unique=True),
        Index("ix_vocabularies_word", "word"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    word = Column(String, nullable=False)
    word_type = Column(String, nullable=True)
    ipa = Column(String)
    audio_url = Column(String)
    image_url = Column(String)
    definition_vi = Column(Text, nullable=True)
    example_sentence = Column(Text)
    example_translation_vi = Column(Text)
    source_subtitle_id = Column(Integer, ForeignKey("subtitles.id", ondelete="SET NULL"), nullable=True)

    source_subtitle = relationship("Subtitle", back_populates="vocabulary_items")
    notebook_items = relationship("NotebookItem", back_populates="vocabulary", cascade="all, delete-orphan")
    progress_entries = relationship("VocabularyProgress", back_populates="vocabulary", cascade="all, delete-orphan")
    topic_entries = relationship("VocabularyTopicWord", back_populates="vocabulary", cascade="all, delete-orphan")

class Notebook(Base, TimeStampMixin):
    """
    Represents a user's vocabulary notebook collection.

    Attributes:
        id (int): The unique identifier of the notebook.
        user_id (int): The user identifier.
        name (str): The notebook name.
        description (str): The notebook description.
    """
    __tablename__ = "notebooks"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_notebooks_user_id_name"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)

    user = relationship("User", back_populates="notebooks")
    items = relationship("NotebookItem", back_populates="notebook", cascade="all, delete-orphan")


class NotebookItem(Base, TimeStampMixin):
    """
    Represents a vocabulary item in a notebook.

    Attributes:
        id (int): The unique identifier.
        notebook_id (int): The notebook identifier.
        vocabulary_id (int): The vocabulary identifier.
        context_sentence (str): Sentence context where the word was found.
        note (str): User's personal note.
    """
    __tablename__ = "notebook_items"
    __table_args__ = (UniqueConstraint("notebook_id", "vocabulary_id", name="uq_notebook_items_notebook_id_vocabulary_id"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id", ondelete="CASCADE"), nullable=False)
    context_sentence = Column(Text)
    note = Column(Text)

    notebook = relationship("Notebook", back_populates="items")
    vocabulary = relationship("Vocabulary", back_populates="notebook_items")


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

    id = Column(Integer, autoincrement=True, primary_key=True)
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
    id = Column(Integer, autoincrement=True, primary_key=True)
    vocabulary_progress_id = Column(Integer, ForeignKey("vocabulary_progress.id", ondelete="CASCADE"), nullable=False)
    rating = Column(String, nullable=False)
    response_ms = Column(Integer)
    reviewed_at = Column(DateTime(timezone=True), nullable=False)

    vocabulary_progress = relationship("VocabularyProgress", back_populates="review_logs")


class VocabularyBook(Base, TimeStampMixin):
    """
    Represents a curated vocabulary collection (e.g. "600 Essential Words for the TOEIC").

    Attributes:
        id (int): The unique identifier of the book.
        name (str): Display name of the collection.
        slug (str): URL-friendly unique identifier used in API routes.
        description (str): Short description of the collection.
        category (str): Category from VocabularyBookCategory enum (TOEIC, IELTS, ...).
        image_url (str): URL to the book cover image shown on the listing page.
        deleted (bool): Soft-delete flag; deleted books are hidden from users.
    """
    __tablename__ = "vocabulary_books"
    __table_args__ = (UniqueConstraint("slug", name="uq_vocabulary_books_slug"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, nullable=False, default=VocabularyBookCategory.TOEIC.value)
    image_url = Column(String)
    deleted = Column(Boolean, nullable=False, default=False)

    topics = relationship("VocabularyTopic", back_populates="book", cascade="all, delete-orphan")


class VocabularyTopic(Base, TimeStampMixin):
    """
    Represents a topic/set within a vocabulary book (e.g. "01. Contract").

    Attributes:
        id (int): The unique identifier of the topic.
        book_id (int): The parent book identifier.
        name (str): Display name of the topic (e.g. "Contract").
        slug (str): URL-friendly identifier unique within a book (e.g. "toeic-600-01-contract").
        order_num (int): Sequential position within the book.
        word_count (int): Cached count of words; updated after import or word changes.
    """
    __tablename__ = "vocabulary_topics"
    __table_args__ = (
        UniqueConstraint("book_id", "slug", name="uq_vocabulary_topics_book_id_slug"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    book_id = Column(Integer, ForeignKey("vocabulary_books.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    order_num = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=False, default=0)

    book = relationship("VocabularyBook", back_populates="topics")
    topic_words = relationship("VocabularyTopicWord", back_populates="topic", cascade="all, delete-orphan")


class VocabularyTopicWord(Base):
    """
    Junction table linking vocabularies to vocabulary_topics (many-to-many).

    A single vocabulary word can appear in multiple topics across
    different books.

    Attributes:
        id (int): The unique identifier.
        topic_id (int): The topic this word belongs to.
        vocabulary_id (int): The vocabulary word.
        order_num (int): Controls display order of the word within the topic.
    """
    __tablename__ = "vocabulary_topic_words"
    __table_args__ = (
        UniqueConstraint("topic_id", "vocabulary_id", name="uq_vocabulary_topic_words_topic_id_vocabulary_id"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    topic_id = Column(Integer, ForeignKey("vocabulary_topics.id", ondelete="CASCADE"), nullable=False)
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id", ondelete="CASCADE"), nullable=False)
    order_num = Column(Integer, nullable=False, default=0)

    topic = relationship("VocabularyTopic", back_populates="topic_words")
    vocabulary = relationship("Vocabulary", back_populates="topic_entries")
