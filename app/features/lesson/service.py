import math
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_record,
    async_delete_one_record_by,
    async_get_many_records_by,
    async_get_one_record_by,
    async_get_one_record_by_id,
    async_update_one_record,
    transactional,
)
from app.features.lesson.model import (
    Category,
    Lesson,
    LessonAnswer,
    LessonProgress,
    LessonSession,
    Subtitle,
)
from app.features.lesson.schemas import (
    LessonAnswerRequest,
    LessonAnswerResponse,
    LessonDetailResponse,
    LessonPaginationFilter,
    LessonProgressRequest,
    LessonProgressResponse,
    LessonResumeResponse,
    LessonSessionRequest,
    LessonSessionResponse,
    LessonSubtitleResponse,
    LessonSummaryResponse,
    YouTubeLessonImportRequest,
)
from app.features.lesson.youtube import load_youtube_lesson_source
from app.utils.common import page_size_to_offset_limit
from app.utils.constants import ContentStatus, LessonSessionStatus, SortOrder


def _slugify(value: str) -> str:
    """
    Convert text to a lowercase ASCII slug with hyphen-separated words.

    Args:
        value (str): The text to convert to a URL slug.

    Returns:
        str: The URL-safe slug with no leading or trailing hyphens.
    """
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized.lower())).strip("-")


def _build_lesson_detail_response(
    lesson: Lesson,
    subtitles: list[Subtitle],
) -> LessonDetailResponse:
    """
    Build lesson details with every subtitle in timeline order.

    Args:
        lesson (Lesson): The lesson record used to build the response.
        subtitles (list[Subtitle]): The lesson's subtitle records to order by sequence
            and start time.

    Returns:
        LessonDetailResponse: The lesson details with every subtitle in transcript
            order.
    """
    ordered_subtitles = sorted(
        subtitles, key=lambda item: (item.sequence, item.start_ms)
    )
    subtitle_responses = [
        LessonSubtitleResponse(
            id=subtitle.id,
            sequence=subtitle.sequence,
            start_ms=subtitle.start_ms,
            end_ms=subtitle.end_ms,
            content_en=subtitle.content_en,
            translation_vi=subtitle.translation_vi,
        )
        for subtitle in ordered_subtitles
    ]
    return LessonDetailResponse(
        id=lesson.id,
        title=lesson.title,
        slug=lesson.slug,
        description=lesson.description,
        video_provider=lesson.video_provider,
        video_id=lesson.video_id,
        video_url=lesson.video_url,
        thumbnail_url=lesson.thumbnail_url,
        duration_seconds=lesson.duration_seconds,
        difficulty=lesson.difficulty,
        subtitle_count=len(subtitle_responses),
        subtitles=subtitle_responses,
    )


def _build_lesson_summary_response(
    lesson: Lesson,
    subtitle_count: int,
    topic: Optional[str] = None,
) -> LessonSummaryResponse:
    """
    Build a lesson catalog card with its subtitle count and optional topic.

    Args:
        lesson (Lesson): The associated lesson.
        subtitle_count (int): The number of subtitles associated with the lesson.
        topic (Optional[str]): The optional category name displayed on the lesson card.

    Returns:
        LessonSummaryResponse: The lesson's catalog summary.
    """
    return LessonSummaryResponse(
        id=lesson.id,
        title=lesson.title,
        slug=lesson.slug,
        video_provider=lesson.video_provider,
        video_id=lesson.video_id,
        thumbnail_url=lesson.thumbnail_url,
        duration_seconds=lesson.duration_seconds,
        difficulty=lesson.difficulty,
        subtitle_count=subtitle_count,
        views_count=lesson.views_count,
        channel_name=lesson.channel_name,
        topic=topic,
    )


class LessonService(object):
    """
    Import and read video lessons with complete timed transcripts.

    Imports YouTube sources, tracks playback progress, and manages lesson sessions and
    subtitle answers.
    """

    @staticmethod
    async def _get_published_lesson(lesson_slug: str, session: AsyncSession) -> Lesson:
        """
        Look up a published lesson by its slug.

        Args:
            lesson_slug (str): The URL slug identifying the lesson.
            session (AsyncSession): The database session used for record operations.

        Returns:
            Lesson: The matching published lesson.

        Raises:
            HTTPException: If no published lesson matches the slug.
        """
        return await async_get_one_record_by(
            Lesson,
            [
                Lesson.slug == lesson_slug,
                Lesson.status == ContentStatus.PUBLISHED.value,
            ],
            session,
            not_found_msg="Lesson not found",
            raise_if_not_found=True,
        )

    @staticmethod
    async def _get_user_session(
        user_id: int, lesson_id: int, session_id: int, session: AsyncSession
    ) -> LessonSession:
        """
        Look up a lesson session belonging to the specified user and lesson.

        Args:
            user_id (int): The identifier of the user who owns the record.
            lesson_id (int): The identifier of the associated lesson.
            session_id (int): The identifier of the lesson practice session.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonSession: The matching practice session.

        Raises:
            HTTPException: If the session does not belong to the user and lesson or does
                not exist.
        """
        return await async_get_one_record_by(
            LessonSession,
            [
                LessonSession.id == session_id,
                LessonSession.lesson_id == lesson_id,
                LessonSession.user_id == user_id,
            ],
            session,
            not_found_msg="Lesson session not found",
            raise_if_not_found=True,
        )

    @staticmethod
    async def get_detail(
        lesson_slug: str,
        session: AsyncSession,
    ) -> LessonDetailResponse:
        """
        Retrieve a published lesson and build its ordered transcript response.

        Args:
            lesson_slug (str): The URL slug identifying the lesson.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonDetailResponse: Lesson metadata and ordered subtitles.

        Raises:
            HTTPException: If no published lesson matches the slug.
        """
        lesson = await LessonService._get_published_lesson(lesson_slug, session)
        subtitles = await async_get_many_records_by(
            Subtitle,
            [Subtitle.lesson_id == lesson.id],
            session,
            raise_if_not_found=False,
        )
        return _build_lesson_detail_response(lesson, subtitles)

    @staticmethod
    async def _build_progress_response(
        lesson: Lesson,
        progress: Optional[LessonProgress],
        session: AsyncSession,
    ) -> LessonProgressResponse:
        """
        Build saved or default progress and find the next eligible subtitle.

        Args:
            lesson (Lesson): The associated lesson.
            progress (Optional[LessonProgress]): The user's saved playback progress, if
                available.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonProgressResponse: Progress enriched with subtitle count and current
                subtitle.
        """
        response = (
            LessonProgressResponse.model_validate(progress)
            if progress
            else LessonProgressResponse(
                lesson_id=lesson.id,
                last_position_seconds=0,
                completion_percent=0,
                completed_at=None,
                last_watched_at=None,
            )
        )
        subtitles = await async_get_many_records_by(
            Subtitle,
            [Subtitle.lesson_id == lesson.id],
            session,
            raise_if_not_found=False,
        )
        response.subtitle_count = len(subtitles)
        if response.completed_at is None and response.completion_percent < 100:
            subtitle = min(
                (
                    subtitle for subtitle in subtitles
                    if subtitle.end_ms > response.last_position_seconds * 1000
                ),
                key=lambda item: (item.sequence, item.start_ms),
                default=None,
            )
            if subtitle:
                response.current_subtitle = LessonSubtitleResponse(
                    id=subtitle.id,
                    sequence=subtitle.sequence,
                    start_ms=subtitle.start_ms,
                    end_ms=subtitle.end_ms,
                    content_en=subtitle.content_en,
                    translation_vi=subtitle.translation_vi,
                )
        return response

    @staticmethod
    async def get_resume(
        user_id: int, session: AsyncSession
    ) -> Optional[LessonResumeResponse]:
        """
        Find the user's latest unfinished progress for a published lesson.

        Args:
            user_id (int): The identifier of the user who owns the record.
            session (AsyncSession): The database session used for record operations.

        Returns:
            Optional[LessonResumeResponse]: Lesson and progress details, or None if no
                eligible record exists.
        """
        latest_progress_id = (
            select(LessonProgress.id)
            .where(
                LessonProgress.user_id == user_id,
                LessonProgress.last_watched_at.is_not(None),
                LessonProgress.completed_at.is_(None),
                LessonProgress.completion_percent < 100,
                LessonProgress.lesson.has(Lesson.status == ContentStatus.PUBLISHED.value),
            )
            .order_by(LessonProgress.last_watched_at.desc(), LessonProgress.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        progress = await async_get_one_record_by(
            LessonProgress,
            [LessonProgress.id == latest_progress_id],
            session,
            raise_if_not_found=False,
            options=[joinedload(LessonProgress.lesson).joinedload(Lesson.category)],
        )
        if progress is None:
            return None
        lesson = progress.lesson
        topic = lesson.category.name if lesson.category else None
        response = await LessonService._build_progress_response(lesson, progress, session)
        return LessonResumeResponse(
            lesson=_build_lesson_summary_response(lesson, response.subtitle_count, topic),
            progress=response,
        )

    @classmethod
    async def get_progress(
        cls,
        user_id: int, 
        lesson_slug: str, 
        session: AsyncSession
    ) -> LessonProgressResponse:
        """
        Retrieve a user's progress or defaults without creating a progress record.

        Args:
            user_id (int): The identifier of the user who owns the record.
            lesson_slug (str): The URL slug identifying the lesson.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonProgressResponse: Saved or default progress and subtitle context.

        Raises:
            HTTPException: If no published lesson matches the slug.
        """
        lesson = await cls._get_published_lesson(lesson_slug, session)
        progress = await async_get_one_record_by(
            LessonProgress,
            [LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson.id],
            session,
            raise_if_not_found=False,
        )
        return await cls._build_progress_response(lesson, progress, session)

    @classmethod
    @transactional()
    async def save_progress(
        cls,
        user_id: int,
        lesson_slug: str,
        data: LessonProgressRequest,
        session: AsyncSession,
    ) -> LessonProgressResponse:
        """
        Persist playback position, completion percentage, and viewing timestamps.

        Args:
            user_id (int): The identifier of the user who owns the record.
            lesson_slug (str): The URL slug identifying the lesson.
            data (LessonProgressRequest): The playback position to persist.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonProgressResponse: The saved progress with subtitle context.

        Raises:
            HTTPException: If the published lesson is missing or the position exceeds
                its duration.
        """
        lesson = await cls._get_published_lesson(lesson_slug, session)
        if (
            lesson.duration_seconds
            and data.last_position_seconds > lesson.duration_seconds
        ):
            raise HTTPException(
                status_code=422, detail="Position exceeds lesson duration"
            )

        now = datetime.now(timezone.utc)
        completion = (
            round(data.last_position_seconds / lesson.duration_seconds * 100, 2)
            if lesson.duration_seconds
            else 0
        )
        progress = await async_get_one_record_by(
            LessonProgress,
            [LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson.id],
            session,
            raise_if_not_found=False,
        )
        values = {
            "last_position_seconds": data.last_position_seconds,
            "completion_percent": completion,
            "last_watched_at": now,
        }
        if completion >= 100 and not (progress and progress.completed_at):
            values["completed_at"] = now
        if progress:
            progress = await async_update_one_record(
                LessonProgress, progress.id, values, session
            )
        else:
            progress = await async_create_record(
                LessonProgress,
                {"user_id": user_id, "lesson_id": lesson.id, **values},
                session,
            )
        return await cls._build_progress_response(lesson, progress, session)

    @classmethod
    @transactional()
    async def start_session(
        cls,
        user_id: int,
        lesson_slug: str,
        data: LessonSessionRequest,
        session: AsyncSession,
    ) -> LessonSessionResponse:
        """
        Create a practice session with its mode and total subtitle count.

        Args:
            user_id (int): The identifier of the user who owns the record.
            lesson_slug (str): The URL slug identifying the lesson.
            data (LessonSessionRequest): The practice mode for the new lesson session.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonSessionResponse: The newly created lesson session.

        Raises:
            HTTPException: If no published lesson matches the slug.
        """
        lesson = await cls._get_published_lesson(lesson_slug, session)
        total_count = (
            await session.exec(
                select(func.count(Subtitle.id)).where(Subtitle.lesson_id == lesson.id)
            )
        ).one()
        lesson_session = await async_create_record(
            LessonSession,
            {
                "user_id": user_id,
                "lesson_id": lesson.id,
                "mode": data.mode.value,
                "status": LessonSessionStatus.STARTED.value,
                "total_count": total_count,
                "started_at": datetime.now(timezone.utc),
            },
            session,
        )
        return cls.model_validate(lesson_session)

    @classmethod
    @transactional()
    async def submit_answer(
        cls,
        user_id: int,
        lesson_slug: str,
        session_id: int,
        data: LessonAnswerRequest,
        session: AsyncSession,
    ) -> LessonAnswerResponse:
        """
        Grade a subtitle answer, count attempts, and update the session's scores.

        Args:
            user_id (int): The identifier of the user who owns the record.
            lesson_slug (str): The URL slug identifying the lesson.
            session_id (int): The identifier of the lesson practice session.
            data (LessonAnswerRequest): The subtitle identifier and submitted answer
                text.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonAnswerResponse: The saved answer and grading details.

        Raises:
            HTTPException: If the lesson, owned session, or subtitle is missing, or the
                session is inactive.
        """
        lesson = await cls._get_published_lesson(lesson_slug, session)
        lesson_session = await cls._get_user_session(
            user_id, lesson.id, session_id, session
        )
        if lesson_session.status != LessonSessionStatus.STARTED.value:
            raise HTTPException(status_code=409, detail="Lesson session is not active")

        subtitle = await async_get_one_record_by(
            Subtitle,
            [Subtitle.id == data.subtitle_id, Subtitle.lesson_id == lesson.id],
            session,
            not_found_msg="Subtitle not found",
            raise_if_not_found=True,
        )
        expected = " ".join(subtitle.content_en.casefold().split())
        submitted = " ".join(data.user_input.casefold().split())
        accuracy = round(SequenceMatcher(None, submitted, expected).ratio() * 100, 2)
        answer = await async_get_one_record_by(
            LessonAnswer,
            [
                LessonAnswer.session_id == session_id,
                LessonAnswer.subtitle_id == subtitle.id,
            ],
            session,
            raise_if_not_found=False,
        )
        values = {
            "user_input": data.user_input,
            "accuracy_score": accuracy,
            "is_correct": submitted == expected,
            "attempt_count": answer.attempt_count + 1 if answer else 1,
            "answered_at": datetime.now(timezone.utc),
        }
        if answer:
            answer = await async_update_one_record(
                LessonAnswer, answer.id, values, session
            )
        else:
            answer = await async_create_record(
                LessonAnswer,
                {"session_id": session_id, "subtitle_id": subtitle.id, **values},
                session,
            )

        answers = await async_get_many_records_by(
            LessonAnswer,
            [LessonAnswer.session_id == session_id],
            session,
            raise_if_not_found=False,
        )
        lesson_session.correct_count = sum(answer.is_correct for answer in answers)
        lesson_session.score = round(
            sum(float(answer.accuracy_score or 0) for answer in answers) / len(answers),
            2,
        )
        return LessonAnswerResponse.model_validate(answer)

    @classmethod
    @transactional()
    async def complete_session(
        cls,
        user_id: int,
        lesson_slug: str,
        session_id: int,
        session: AsyncSession,
    ) -> LessonSessionResponse:
        """
        Mark an owned lesson session complete and record its elapsed duration.

        Args:
            user_id (int): The identifier of the user who owns the record.
            lesson_slug (str): The URL slug identifying the lesson.
            session_id (int): The identifier of the lesson practice session.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonSessionResponse: The completed session; repeated completion preserves
                its timestamps.

        Raises:
            HTTPException: If the published lesson or the user's session is not found.
        """
        lesson = await cls._get_published_lesson(lesson_slug, session)
        lesson_session = await cls._get_user_session(
            user_id, lesson.id, session_id, session
        )
        if lesson_session.status == LessonSessionStatus.STARTED.value:
            now = datetime.now(timezone.utc)
            started_at = lesson_session.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            lesson_session.status = LessonSessionStatus.COMPLETED.value
            lesson_session.completed_at = now
            lesson_session.duration_seconds = max(
                0, int((now - started_at).total_seconds())
            )
        return LessonSessionResponse.model_validate(lesson_session)

    @staticmethod
    def _build_where_clause(filters: LessonPaginationFilter) -> list:
        """
        Build lesson search conditions for both listing and counting.

        Args:
            filters (LessonPaginationFilter): The lesson catalog's search, sorting, and
                pagination criteria.

        Returns:
            list: SQL conditions restricting results to published lessons and the search
                keyword.
        """
        where_clause = [Lesson.status == ContentStatus.PUBLISHED.value]
        if filters.keyword:
            where_clause.append(
                or_(
                    Lesson.title.icontains(filters.keyword, autoescape=True),
                    Lesson.channel_name.icontains(filters.keyword, autoescape=True),
                    Category.name.icontains(filters.keyword, autoescape=True),
                )
            )
        return where_clause

    @classmethod
    async def list_lessons(
        cls,
        filters: LessonPaginationFilter,
        session: AsyncSession,
    ) -> tuple[list[LessonSummaryResponse], int, int]:
        """
        List all lessons with their summary and subtitle count.

        Args:
            filters (LessonPaginationFilter): Pagination parameters.
            session (AsyncSession): Active database session.

        Returns:
            tuple[list[LessonSummaryResponse], int, int]: Page items, total
                lesson count, and total page count.
        """
        where_clause = cls._build_where_clause(filters)
        sort_column = getattr(Lesson, filters.sort_by)
        ordering = [
            sort_column.desc()
            if filters.sort_order == SortOrder.DESCEND
            else sort_column.asc()
        ]
        if filters.sort_by == "views_count":
            ordering.append(Lesson.published_at.desc())
        ordering.append(Lesson.id.desc())
        query = (
            select(Lesson, func.count(Subtitle.id), Category.name)
            .outerjoin(Subtitle, Subtitle.lesson_id == Lesson.id)
            .outerjoin(Category, Category.id == Lesson.category_id)
            .where(*where_clause)
            .group_by(Lesson.id, Category.name)
            .order_by(*ordering)
        )
        count_query = (
            select(func.count(Lesson.id))
            .outerjoin(Category, Category.id == Lesson.category_id)
            .where(*where_clause)
        )
        total = (await session.exec(count_query)).one()

        pages = -(-total // filters.page_size) if total else 0
        offset, limit = page_size_to_offset_limit(filters.page, filters.page_size)
        query = query.offset(offset).limit(limit)

        rows = (await session.exec(query)).all()
        lessons = [
            _build_lesson_summary_response(lesson, subtitle_count, topic)
            for lesson, subtitle_count, topic in rows
        ]
        return lessons, total, pages

    @staticmethod
    @transactional()
    async def import_youtube(
        user_id: int,
        data: YouTubeLessonImportRequest,
        session: AsyncSession,
    ) -> LessonDetailResponse:
        """
        Import one YouTube video and persist its complete English transcript.

        Args:
            user_id (int): The identifier of the user whose records are requested.
            data (YouTubeLessonImportRequest): The video URL, lesson metadata, and
                translation settings.
            session (AsyncSession): The database session used for record operations.

        Returns:
            LessonDetailResponse: The imported lesson and its complete timed transcript.

        Raises:
            HTTPException: If the source video or transcript is unavailable, translation
                fails, the category is missing, the title is blank, or the imported
                lesson conflicts with an existing record.
        """
        source = await load_youtube_lesson_source(
            data.video_url,
            data.translate_to_vi,
        )
        existing_lesson = await async_get_one_record_by(
            Lesson,
            [
                Lesson.video_provider == "youtube",
                Lesson.video_id == source.video_id,
            ],
            session,
            raise_if_not_found=False,
        )
        if existing_lesson is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This YouTube video has already been imported",
            )

        if data.category_id is not None:
            category = await async_get_one_record_by_id(
                Category,
                data.category_id,
                session,
                raise_if_not_found=False,
            )
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found",
                )

        title = data.title or source.title
        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The YouTube video has no usable title",
            )

        slug = (_slugify(title) or f"youtube-{source.video_id}")[:255]
        slug_exists = await async_get_one_record_by(
            Lesson,
            [Lesson.slug == slug],
            session,
            raise_if_not_found=False,
        )
        if slug_exists is not None:
            slug = f"{slug[:244].rstrip('-')}-{source.video_id}"

        subtitles = []
        for sequence, segment in enumerate(source.segments, start=1):
            start_ms = round(segment.start_seconds * 1000)
            end_ms = max(round(segment.end_seconds * 1000), start_ms + 1)
            subtitles.append(
                Subtitle(
                    sequence=sequence,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    content_en=segment.content_en,
                    translation_vi=segment.translation_vi,
                )
            )

        try:
            lesson = await async_create_record(
                Lesson,
                {
                    "category_id": data.category_id,
                    "title": title,
                    "slug": slug,
                    "description": data.description,
                    "video_provider": "youtube",
                    "video_id": source.video_id,
                    "channel_name": source.channel_name,
                    "video_url": f"https://www.youtube.com/watch?v={source.video_id}",
                    "thumbnail_url": source.thumbnail_url,
                    "duration_seconds": math.ceil(source.segments[-1].end_seconds),
                    "difficulty": data.difficulty.value,
                    "status": ContentStatus.PUBLISHED.value,
                    "views_count": 0,
                    "published_at": datetime.now(timezone.utc),
                    "created_by": user_id,
                    "updated_by": user_id,
                    "subtitles": subtitles,
                },
                session,
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The lesson conflicts with an existing record",
            )

        return _build_lesson_detail_response(lesson, subtitles)

    @staticmethod
    async def delete_lesson(
        lesson_slug: str,
        session: AsyncSession,
    ) -> None:
        """
        Delete an imported lesson and its dependent records.

        Args:
            lesson_slug (str): The URL slug identifying the lesson to delete.
            session (AsyncSession): The database session used for record operations.

        Raises:
            HTTPException: If no lesson matches the supplied slug.
        """
        await async_delete_one_record_by(
            Lesson,
            session,
            search_criteria=[Lesson.slug == lesson_slug],
        )
