from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import ContentStatus, TagType


class Category(Base, TimeStampMixin):
    """
    Represents a lesson category.

    Attributes:
        id (int): The unique identifier of the category.
        parent_id (int): The parent category identifier for hierarchical structure.
        name (str): The category name.
        slug (str): The URL-friendly slug.
        description (str): The category description.
        display_order (int): The display order for sorting.
        is_active (bool): Whether the category is active.
    """
    __tablename__ = "Category"
    id = Column(Integer, autoincrement=True, primary_key=True)
    parent_id = Column(Integer, ForeignKey("Category.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    description = Column(Text)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    lessons = relationship("Lesson", back_populates="category")


class Tag(Base, TimeStampMixin):
    """
    Represents a tag for categorizing lessons.

    Attributes:
        id (int): The unique identifier of the tag.
        name (str): The tag name.
        slug (str): The URL-friendly slug.
        type (str): The tag type (topic, skill, accent, source, grammar).
    """
    __tablename__ = "Tag"
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    type = Column(String, nullable=False, default=TagType.TOPIC.value)

    lesson_tags = relationship("LessonTag", back_populates="tag", cascade="all, delete-orphan")
    lessons = relationship("Lesson", secondary=lambda: LessonTag.__table__, back_populates="tags", viewonly=True)


class Lesson(Base, TimeStampMixin):
    """
    Represents a video-based English lesson.

    Attributes:
        id (int): The unique identifier of the lesson.
        category_id (int): The category identifier.
        title (str): The lesson title.
        slug (str): The URL-friendly slug.
        description (str): The lesson description.
        video_provider (str): Video hosting provider (e.g., youtube).
        video_id (str): The video identifier on the provider platform.
        video_url (str): Full video URL.
        thumbnail_url (str): Video thumbnail URL.
        duration_seconds (int): Video duration in seconds.
        difficulty (str): The difficulty level (A1, A2, B1, B2, C1, C2).
        status (str): Content status (draft, published, archived).
        views_count (int): Number of views.
        published_at (datetime): When the lesson was published.
        created_by (int): User ID who created the lesson.
        updated_by (int): User ID who last updated the lesson.
    """
    __tablename__ = "Lesson"
    __table_args__ = (
        UniqueConstraint("video_provider", "video_id", name="uq_lessons_video_provider_video_id"),
        Index("lessons_idx", "status", "published_at"),
        Index("lessons_category_idx", "category_id", "status"),
        Index("lessons_difficulty_idx", "difficulty", "status"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    category_id = Column(Integer, ForeignKey("Category.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    description = Column(Text)
    video_provider = Column(String, nullable=False, default="youtube")
    video_id = Column(String, nullable=False)
    video_url = Column(String)
    thumbnail_url = Column(String)
    duration_seconds = Column(Integer, nullable=False, default=0)
    difficulty = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ContentStatus.DRAFT.value)
    views_count = Column(Integer, nullable=False, default=0)
    published_at = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("User.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("User.id", ondelete="SET NULL"), nullable=True)

    category = relationship("Category", back_populates="lessons")
    lesson_tags = relationship("LessonTag", back_populates="lesson", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=lambda: LessonTag.__table__, back_populates="lessons", viewonly=True)
    subtitles = relationship("Subtitle", back_populates="lesson", cascade="all, delete-orphan", order_by="Subtitle.sequence")
    learning_progress = relationship("LearningProgress", back_populates="lesson", cascade="all, delete-orphan")
    practice_sessions = relationship("PracticeSession", back_populates="lesson", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="lesson")


class LessonTag(Base, TimeStampMixin):
    """
    Represents the relationship between lessons and tags.

    Attributes:
        id (int): The unique identifier of the lesson-tag relationship.
        lesson_id (int): The lesson identifier.
        tag_id (int): The tag identifier.
    """
    __tablename__ = "LessonTag"
    __table_args__ = (UniqueConstraint("lesson_id", "tag_id", name="uq_lesson_tags_lesson_id_tag_id"),)

    id = Column(Integer, autoincrement=True, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("Tag.id", ondelete="CASCADE"), nullable=False)

    lesson = relationship("Lesson", back_populates="lesson_tags")
    tag = relationship("Tag", back_populates="lesson_tags")


class Subtitle(Base, TimeStampMixin):
    """
    Represents a subtitle segment for a lesson video.

    Attributes:
        id (int): The unique identifier of the subtitle.
        lesson_id (int): The lesson identifier.
        sequence (int): The sequence number of this subtitle segment.
        start_ms (int): Start time in milliseconds.
        end_ms (int): End time in milliseconds.
        content_en (str): English subtitle content.
        translation_vi (str): Vietnamese translation.
    """
    __tablename__ = "Subtitle"
    __table_args__ = (
        UniqueConstraint("lesson_id", "sequence", name="uq_subtitles_lesson_id_sequence"),
        CheckConstraint("start_ms >= 0", name="start_ms_non_negative"),
        CheckConstraint("end_ms > start_ms", name="end_ms_after_start_ms"),
        Index("subtitles_idx", "lesson_id", "start_ms"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    content_en = Column(Text, nullable=False)
    translation_vi = Column(Text)

    lesson = relationship("Lesson", back_populates="subtitles")
    vocabulary_items = relationship("Vocabulary", back_populates="source_subtitle")
    practice_answers = relationship("PracticeAnswer", back_populates="subtitle")
