from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.constants import DifficultyLevel, LessonSessionMode, SortOrder


class YouTubeLessonImportRequest(BaseModel):
    """
    Admin request for importing one public YouTube lesson.

    Attributes:
        video_url (str): The source video URL.
        title (Optional[str]): The lesson's display title.
        description (Optional[str]): The description of the resource.
        difficulty (DifficultyLevel): The lesson's CEFR difficulty level.
        category_id (Optional[int]): The category identifier assigned to the imported
            lesson, if supplied.
        translate_to_vi (bool): Whether to generate Vietnamese subtitle translations
            during import.
    """

    video_url: str = Field(..., min_length=1, max_length=500)
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.B1
    category_id: Optional[int] = Field(default=None, ge=1)
    translate_to_vi: bool = True

    @field_validator("video_url", mode="before")
    @classmethod
    def strip_video_url(cls, value: str) -> str:
        """
        Trim surrounding whitespace from a string video URL.

        Args:
            value (str): The video URL supplied before field validation.

        Returns:
            str: The trimmed URL; non-string input is passed through for validation.
        """
        return value.strip() if isinstance(value, str) else value


class LessonSubtitleResponse(BaseModel):
    """
    One timed sentence in a lesson video.

    Attributes:
        id (int): The unique identifier of the record.
        sequence (int): The subtitle's position in the transcript.
        start_ms (int): The subtitle's start time in milliseconds.
        end_ms (int): The subtitle's end time in milliseconds.
        content_en (str): The English subtitle text.
        translation_vi (Optional[str]): The Vietnamese translation of the source text or
            word.
    """

    id: int
    sequence: int
    start_ms: int
    end_ms: int
    content_en: str
    translation_vi: Optional[str]


class LessonDetailResponse(BaseModel):
    """
    Lesson details including the complete timed transcript.

    Attributes:
        id (int): The unique identifier of the record.
        title (str): The lesson's display title.
        slug (str): The URL slug identifying the resource.
        description (Optional[str]): The description of the resource.
        video_provider (str): The video hosting provider.
        video_id (str): The identifier of the source video.
        video_url (Optional[str]): The source video URL.
        thumbnail_url (Optional[str]): The video thumbnail URL, if available.
        duration_seconds (int): The duration of the video or activity in seconds.
        difficulty (str): The lesson's CEFR difficulty level.
        subtitle_count (int): The number of subtitles in the lesson.
        subtitles (List[LessonSubtitleResponse]): The lesson's timed transcript in
            sequence order.
    """

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
    """
    A lesson card for the imported video catalog.

    Attributes:
        id (int): The unique identifier of the record.
        title (str): The lesson's display title.
        slug (str): The URL slug identifying the resource.
        video_provider (str): The video hosting provider.
        video_id (str): The identifier of the source video.
        thumbnail_url (Optional[str]): The video thumbnail URL, if available.
        duration_seconds (int): The duration of the video or activity in seconds.
        difficulty (str): The lesson's CEFR difficulty level.
        subtitle_count (int): The number of subtitles in the lesson.
        views_count (int): The number of views recorded for the lesson.
        channel_name (Optional[str]): The video's source channel name, if available.
        topic (Optional[str]): The topic associated with the lesson or review session.
    """

    id: int
    title: str
    slug: str
    video_provider: str
    video_id: str
    thumbnail_url: Optional[str]
    duration_seconds: int
    difficulty: str
    subtitle_count: int
    views_count: int
    channel_name: Optional[str]
    topic: Optional[str]


class LessonPaginationFilter(BaseModel):
    """
    Pagination, search, and ordering for the lesson catalog.

    Attributes:
        page (int): The current page number, starting at one.
        page_size (int): The maximum number of items returned per page.
        keyword (Optional[str]): The search keyword used to filter results.
        sort_by (Literal['published_at', 'views_count']): The field used to sort
            matching lessons.
        sort_order (SortOrder): Whether matching lessons are sorted in ascending or
            descending order.
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    keyword: Optional[str] = Field(default=None, max_length=100)
    sort_by: Literal["published_at", "views_count"] = "published_at"
    sort_order: SortOrder = SortOrder.DESCEND

    @field_validator("keyword")
    @classmethod
    def strip_keyword(cls, value: Optional[str]) -> Optional[str]:
        """
        Trim the search keyword and treat blank input as no filter.

        Args:
            value (Optional[str]): The optional catalog search keyword.

        Returns:
            Optional[str]: The trimmed keyword, or None for missing or blank input.
        """
        if value is None:
            return None
        return value.strip() or None


class LessonListMeta(BaseModel):
    """
    Pagination metadata for the published lesson catalog.

    Attributes:
        total (int): The total number of matching records.
        page (int): The current page number, starting at one.
        page_size (int): The maximum number of records returned per page.
        pages (int): The total number of pages matching the filter.
    """

    total: int
    page: int
    page_size: int
    pages: int


class LessonListResponse(BaseModel):
    """
    Response containing lesson catalog cards and pagination metadata.

    Attributes:
        data (List[LessonSummaryResponse]): The lesson cards returned for the current
            page.
        metadata (LessonListMeta): Pagination details for the result set.
    """

    data: List[LessonSummaryResponse]
    metadata: LessonListMeta


class LessonProgressRequest(BaseModel):
    """
    Request to save a lesson's playback position.

    Attributes:
        last_position_seconds (int): The saved playback position in seconds from the
            start of the lesson.
    """

    last_position_seconds: int = Field(..., ge=0)


class LessonProgressResponse(BaseModel):
    """
    Response containing playback progress and the current subtitle.

    Attributes:
        lesson_id (int): The identifier of the associated lesson.
        last_position_seconds (int): The saved playback position in seconds from the
            start of the lesson.
        completion_percent (Decimal): The percentage of the lesson duration reached by
            the saved position.
        completed_at (Optional[datetime]): The completion timestamp, or None while
            unfinished.
        last_watched_at (Optional[datetime]): The timestamp of the user's latest saved
            playback position.
        subtitle_count (int): The number of subtitles associated with the lesson.
        current_subtitle (Optional[LessonSubtitleResponse]): The next subtitle whose end
            follows the saved position, if the lesson is unfinished.
    """

    model_config = ConfigDict(from_attributes=True)

    lesson_id: int
    last_position_seconds: int
    completion_percent: Decimal
    completed_at: Optional[datetime]
    last_watched_at: Optional[datetime]
    subtitle_count: int = 0
    current_subtitle: Optional[LessonSubtitleResponse] = None


class LessonResumeResponse(BaseModel):
    """
    Response describing the latest unfinished lesson available to resume.

    Attributes:
        lesson (LessonSummaryResponse): The associated lesson.
        progress (LessonProgressResponse): The user's saved playback progress.
    """

    lesson: LessonSummaryResponse
    progress: LessonProgressResponse


class LessonSessionRequest(BaseModel):
    """
    Request to start a lesson session in the selected practice mode.

    Attributes:
        mode (LessonSessionMode): The selected practice mode.
    """

    mode: LessonSessionMode = LessonSessionMode.DICTATION


class LessonSessionResponse(BaseModel):
    """
    Response containing lesson session status, scores, and timestamps.

    Attributes:
        id (int): The unique record identifier.
        lesson_id (int): The identifier of the associated lesson.
        mode (LessonSessionMode): The selected practice mode.
        status (str): The current lifecycle state.
        score (Optional[Decimal]): The session's aggregate answer accuracy percentage,
            if available.
        correct_count (int): The number of correctly answered subtitles.
        total_count (int): The total number of subtitles in the session.
        duration_seconds (int): The elapsed session duration in seconds.
        started_at (datetime): The timestamp when the session started.
        completed_at (Optional[datetime]): The completion timestamp, or None while
            unfinished.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int
    mode: LessonSessionMode
    status: str
    score: Optional[Decimal]
    correct_count: int
    total_count: int
    duration_seconds: int
    started_at: datetime
    completed_at: Optional[datetime]


class LessonAnswerRequest(BaseModel):
    """
    Request to grade an answer for a subtitle in a lesson session.

    Attributes:
        subtitle_id (int): The identifier of the subtitle being answered.
        user_input (str): The text submitted by the user for the subtitle.
    """

    subtitle_id: int = Field(..., ge=1)
    user_input: str = Field(..., min_length=1)


class LessonAnswerSubmitRequest(LessonAnswerRequest):
    """
    Answer submission with lesson and session identifiers in the request body.

    Attributes:
        lesson_slug (str): The URL slug identifying the lesson.
        session_id (int): The identifier of the lesson practice session.
    """

    lesson_slug: str = Field(..., min_length=1)
    session_id: int = Field(..., ge=1)


class LessonCompleteRequest(BaseModel):
    """
    Request identifying the lesson session to complete.

    Attributes:
        lesson_slug (str): The URL slug identifying the lesson.
        session_id (int): The identifier of the lesson practice session.
    """

    lesson_slug: str = Field(..., min_length=1)
    session_id: int = Field(..., ge=1)


class LessonAnswerResponse(BaseModel):
    """
    Response containing a saved subtitle answer and grading details.

    Attributes:
        subtitle_id (int): The identifier of the subtitle being answered.
        user_input (str): The text submitted by the user for the subtitle.
        accuracy_score (Optional[Decimal]): The answer's similarity to the expected text
            as a percentage.
        is_correct (bool): Whether normalized submitted text matches the expected
            answer.
        attempt_count (int): The number of submissions recorded for this subtitle and
            session.
        answered_at (datetime): The timestamp of the latest answer submission.
    """

    model_config = ConfigDict(from_attributes=True)

    subtitle_id: int
    user_input: str
    accuracy_score: Optional[Decimal]
    is_correct: bool
    attempt_count: int
    answered_at: datetime
