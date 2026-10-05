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
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.model import Base, TimeStampMixin
from app.utils.constants import (
    ContentStatus,
    LessonSessionMode,
    LessonSessionStatus,
    TagType,
)


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
    __table_args__ = (UniqueConstraint("slug", name="uq_categories_slug"),)
    id = Column(Integer, autoincrement=True, primary_key=True)
    parent_id = Column(
        Integer, ForeignKey("Category.id", ondelete="SET NULL"), nullable=True
    )
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
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
    __table_args__ = (UniqueConstraint("slug", name="uq_tags_slug"),)
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    type = Column(String, nullable=False, default=TagType.TOPIC.value)

    lesson_tags = relationship(
        "LessonTag", back_populates="tag", cascade="all, delete-orphan"
    )
    lessons = relationship(
        "Lesson",
        secondary=lambda: LessonTag.__table__,
        back_populates="tags",
        viewonly=True,
    )


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
        channel_name (str): Name of the video channel, when available.
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
        UniqueConstraint("slug", name="uq_lessons_slug"),
        UniqueConstraint(
            "video_provider", "video_id", name="uq_lessons_video_provider_video_id"
        ),
        Index("lessons_idx", "status", "published_at"),
        Index("lessons_category_idx", "category_id", "status"),
        Index("lessons_difficulty_idx", "difficulty", "status"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    category_id = Column(
        Integer, ForeignKey("Category.id", ondelete="SET NULL"), nullable=True
    )
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    description = Column(Text)
    video_provider = Column(String, nullable=False, default="youtube")
    video_id = Column(String, nullable=False)
    channel_name = Column(String, nullable=True)
    video_url = Column(String)
    thumbnail_url = Column(String)
    duration_seconds = Column(Integer, nullable=False, default=0)
    difficulty = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ContentStatus.DRAFT.value)
    views_count = Column(Integer, nullable=False, default=0)
    published_at = Column(DateTime(timezone=True))
    created_by = Column(
        Integer, ForeignKey("User.id", ondelete="SET NULL"), nullable=True
    )
    updated_by = Column(
        Integer, ForeignKey("User.id", ondelete="SET NULL"), nullable=True
    )

    category = relationship("Category", back_populates="lessons")
    lesson_tags = relationship(
        "LessonTag", back_populates="lesson", cascade="all, delete-orphan"
    )
    tags = relationship(
        "Tag",
        secondary=lambda: LessonTag.__table__,
        back_populates="lessons",
        viewonly=True,
    )
    subtitles = relationship(
        "Subtitle",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="Subtitle.sequence",
    )
    lesson_progress = relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )
    lesson_sessions = relationship(
        "LessonSession", back_populates="lesson", cascade="all, delete-orphan"
    )
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
    __table_args__ = (
        UniqueConstraint("lesson_id", "tag_id", name="uq_lesson_tags_lesson_id_tag_id"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    lesson_id = Column(
        Integer, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=False
    )
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
        UniqueConstraint(
            "lesson_id", "sequence", name="uq_subtitles_lesson_id_sequence"
        ),
        CheckConstraint("start_ms >= 0", name="start_ms_non_negative"),
        CheckConstraint("end_ms > start_ms", name="end_ms_after_start_ms"),
        Index("subtitles_idx", "lesson_id", "start_ms"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    lesson_id = Column(
        Integer, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=False
    )
    sequence = Column(Integer, nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    content_en = Column(Text, nullable=False)
    translation_vi = Column(Text)

    lesson = relationship("Lesson", back_populates="subtitles")
    lesson_answers = relationship("LessonAnswer", back_populates="subtitle")


class LessonProgress(Base, TimeStampMixin):
    __tablename__ = "LessonProgress"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "lesson_id", name="uq_lesson_progress_user_id_lesson_id"
        ),
        CheckConstraint(
            "completion_percent >= 0 AND completion_percent <= 100",
            name="completion_percent_range",
        ),
        Index("lesson_progress_idx", "user_id", "last_watched_at"),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(
        Integer, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=False
    )
    last_position_seconds = Column(Integer, nullable=False, default=0)
    completion_percent = Column(Numeric(5, 2), nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True))
    last_watched_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="lesson_progress")


class LessonSession(Base, TimeStampMixin):
    __tablename__ = "LessonSession"

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(
        Integer, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=False
    )
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
    answers = relationship(
        "LessonAnswer", back_populates="session", cascade="all, delete-orphan"
    )


class LessonAnswer(Base, TimeStampMixin):
    __tablename__ = "LessonAnswer"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "subtitle_id", name="uq_lesson_answers_session_id_subtitle_id"
        ),
    )

    id = Column(Integer, autoincrement=True, primary_key=True)
    session_id = Column(
        Integer, ForeignKey("LessonSession.id", ondelete="CASCADE"), nullable=False
    )
    subtitle_id = Column(
        Integer, ForeignKey("Subtitle.id", ondelete="CASCADE"), nullable=False
    )
    user_input = Column(Text, nullable=False)
    accuracy_score = Column(Numeric(5, 2))
    is_correct = Column(Boolean, nullable=False, default=False)
    attempt_count = Column(Integer, nullable=False, default=1)
    answered_at = Column(DateTime(timezone=True), nullable=False)

    session = relationship("LessonSession", back_populates="answers")
    subtitle = relationship("Subtitle", back_populates="lesson_answers")
