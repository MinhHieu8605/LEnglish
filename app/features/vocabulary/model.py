import sqlalchemy as sa
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import VocabularyBookCategory


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
    """
    __tablename__ = "Vocabulary"
    __table_args__ = (
        Index("vocabularies_idx", sa.literal_column("lower(word)"), "word_type", unique=True),
        Index("vocabularies_word_idx", "word"),
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
    word_list_items = relationship("WordListItem", back_populates="vocabulary", cascade="all, delete-orphan")
    review_progress_entries = relationship("ReviewProgress", back_populates="vocabulary", cascade="all, delete-orphan")
    topic_entries = relationship("VocabularyTopicWord", back_populates="vocabulary", cascade="all, delete-orphan")


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
    __tablename__ = "VocabularyBook"
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
    __tablename__ = "VocabularyTopic"
    __table_args__ = (
        UniqueConstraint("book_id", "slug", name="uq_vocabulary_topics_book_id_slug"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    book_id = Column(Integer, ForeignKey("VocabularyBook.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    order_num = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=False, default=0)

    book = relationship("VocabularyBook", back_populates="topics")
    topic_words = relationship("VocabularyTopicWord", back_populates="topic", cascade="all, delete-orphan")
    review_sessions = relationship("ReviewSession", back_populates="topic", cascade="all, delete-orphan")


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
    __tablename__ = "VocabularyTopicWord"
    __table_args__ = (
        UniqueConstraint("topic_id", "vocabulary_id", name="uq_vocabulary_topic_words_topic_id_vocabulary_id"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    topic_id = Column(Integer, ForeignKey("VocabularyTopic.id", ondelete="CASCADE"), nullable=False)
    vocabulary_id = Column(Integer, ForeignKey("Vocabulary.id", ondelete="CASCADE"), nullable=False)
    order_num = Column(Integer, nullable=False, default=0)

    topic = relationship("VocabularyTopic", back_populates="topic_words")
    vocabulary = relationship("Vocabulary", back_populates="topic_entries")
