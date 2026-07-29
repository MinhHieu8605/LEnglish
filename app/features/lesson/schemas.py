from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.constants import DifficultyLevel


class YouTubeLessonImportRequest(BaseModel):
    """Admin request for importing one public YouTube lesson."""

    video_url: str = Field(..., min_length=1, max_length=500)
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.B1
    category_id: Optional[int] = Field(default=None, ge=1)
    translate_to_vi: bool = True

    @field_validator("video_url", mode="before")
    @classmethod
    def strip_video_url(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class LessonSubtitleResponse(BaseModel):
    """One timed sentence in a lesson video."""

    id: int
    sequence: int
    start_ms: int
    end_ms: int
    content_en: str
    translation_vi: Optional[str]


class LessonDetailResponse(BaseModel):
    """Lesson details including the complete timed transcript."""

    id: int
    title: str
    slug: str
    description: Optional[str]
    video_provider: str
    video_id: str
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: int
    difficulty: str
    subtitle_count: int
    subtitles: List[LessonSubtitleResponse] = Field(default_factory=list)


class LessonSummaryResponse(BaseModel):
    """A lesson card for the imported video catalog."""

    id: int
    title: str
    slug: str
    video_provider: str
    video_id: str
    thumbnail_url: Optional[str]
    duration_seconds: int
    difficulty: str
    subtitle_count: int


class LessonPaginationFilter(BaseModel):
    """Pagination parameters for the lesson catalog."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class LessonListMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class LessonListResponse(BaseModel):
    data: List[LessonSummaryResponse]
    metadata: LessonListMeta
