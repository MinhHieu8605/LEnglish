import math
import re
import unicodedata
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_delete_one_record_by,
    async_get_many_records_by,
    async_get_one_record_by,
    async_get_one_record_by_id,
    transactional,
)
from app.features.lesson.model import Category, Lesson, Subtitle
from app.features.lesson.schemas import (
    LessonDetailResponse,
    LessonPaginationFilter,
    LessonSubtitleResponse,
    LessonSummaryResponse,
    YouTubeLessonImportRequest,
)
from app.features.lesson.youtube import (
    TranscriptSegment,
    YouTubeLessonSource,
    load_youtube_lesson_source,
)
from app.utils.common import page_size_to_offset_limit
from app.utils.constants import ContentStatus


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized.lower())).strip("-")


def _build_lesson_detail_response(
    lesson: Lesson,
    subtitles: list[Subtitle],
) -> LessonDetailResponse:
    """Build lesson details with every subtitle in timeline order."""
    ordered_subtitles = sorted(subtitles, key=lambda item: (item.sequence, item.start_ms))
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
) -> LessonSummaryResponse:
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
    )


async def _validate_import(
    video_id: str,
    category_id: int | None,
    session: AsyncSession,
) -> None:
    existing_lesson = await async_get_one_record_by(
        Lesson,
        [
            Lesson.video_provider == "youtube",
            Lesson.video_id == video_id,
        ],
        session,
        raise_if_not_found=False,
    )
    if existing_lesson is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This YouTube video has already been imported",
        )

    if category_id is not None:
        category = await async_get_one_record_by_id(
            Category,
            category_id,
            session,
            raise_if_not_found=False,
        )
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )


def _resolve_title(requested_title: str | None, source_title: str) -> str:
    title = requested_title or source_title
    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The YouTube video has no usable title",
        )
    return title


async def _create_unique_slug(
    title: str,
    video_id: str,
    session: AsyncSession,
) -> str:
    slug = (_slugify(title) or f"youtube-{video_id}")[:255]
    slug_exists = (
        await session.exec(select(Lesson.id).where(Lesson.slug == slug))
    ).first()
    if slug_exists is None:
        return slug
    return f"{slug[:244].rstrip('-')}-{video_id}"


def _build_youtube_lesson(
    user_id: int,
    data: YouTubeLessonImportRequest,
    source: YouTubeLessonSource,
    title: str,
    slug: str,
) -> Lesson:
    return Lesson(
        category_id=data.category_id,
        title=title,
        slug=slug,
        description=data.description,
        video_provider="youtube",
        video_id=source.video_id,
        video_url=f"https://www.youtube.com/watch?v={source.video_id}",
        thumbnail_url=source.thumbnail_url,
        duration_seconds=math.ceil(source.segments[-1].end_seconds),
        difficulty=data.difficulty.value,
        status=ContentStatus.PUBLISHED.value,
        views_count=0,
        published_at=datetime.now(timezone.utc),
        created_by=user_id,
        updated_by=user_id,
    )


def _build_subtitles(
    lesson: Lesson,
    segments: list[TranscriptSegment],
) -> list[Subtitle]:
    subtitles: list[Subtitle] = []
    for sequence, segment in enumerate(segments, start=1):
        start_ms = round(segment.start_seconds * 1000)
        end_ms = max(round(segment.end_seconds * 1000), start_ms + 1)
        subtitles.append(
            Subtitle(
                lesson=lesson,
                sequence=sequence,
                start_ms=start_ms,
                end_ms=end_ms,
                content_en=segment.content_en,
                translation_vi=segment.translation_vi,
            )
        )
    return subtitles


@transactional()
async def _save_imported_lesson(
    lesson: Lesson,
    session: AsyncSession,
) -> None:
    try:
        session.add(lesson)
        await session.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The lesson conflicts with an existing record",
        )


class LessonService(object):
    """Import and read video lessons with complete timed transcripts."""

    @staticmethod
    async def get_detail(
        lesson_slug: str,
        session: AsyncSession,
    ) -> LessonDetailResponse:
        lesson = await async_get_one_record_by(
            Lesson,
            [
                Lesson.slug == lesson_slug,
                Lesson.status == ContentStatus.PUBLISHED.value,
            ],
            session,
            not_found_msg="Lesson not found",
            raise_if_not_found=True,
        )
        subtitles = await async_get_many_records_by(
            Subtitle,
            [Subtitle.lesson_id == lesson.id],
            session,
            order_by=[Subtitle.sequence.asc(), Subtitle.start_ms.asc()],
            raise_if_not_found=False,
        )
        return _build_lesson_detail_response(lesson, subtitles)

    @staticmethod
    async def list_lessons(
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
        published_condition = Lesson.status == ContentStatus.PUBLISHED.value
        query = (
            select(Lesson, func.count(Subtitle.id))
            .outerjoin(Subtitle, Subtitle.lesson_id == Lesson.id)
            .where(published_condition)
            .group_by(Lesson.id)
            .order_by(Lesson.published_at.desc(), Lesson.id.desc())
        )
        count_query = select(func.count(Lesson.id)).where(published_condition)
        total = (await session.exec(count_query)).one()

        pages = -(-total // filters.page_size) if total else 0
        offset, limit = page_size_to_offset_limit(filters.page, filters.page_size)
        query = query.offset(offset).limit(limit)

        rows = (await session.exec(query)).all()
        lessons = [
            _build_lesson_summary_response(lesson, subtitle_count)
            for lesson, subtitle_count in rows
        ]
        return lessons, total, pages

    @staticmethod
    async def import_youtube(
        user_id: int,
        data: YouTubeLessonImportRequest,
        session: AsyncSession,
    ) -> LessonDetailResponse:
        """Import one YouTube video and persist its complete English transcript."""
        source = await load_youtube_lesson_source(
            data.video_url,
            data.translate_to_vi,
        )
        await _validate_import(source.video_id, data.category_id, session)
        title = _resolve_title(data.title, source.title)
        slug = await _create_unique_slug(title, source.video_id, session)
        lesson = _build_youtube_lesson(user_id, data, source, title, slug)
        subtitles = _build_subtitles(lesson, source.segments)
        await _save_imported_lesson(lesson, session)

        return _build_lesson_detail_response(lesson, subtitles)

    @staticmethod
    async def delete_lesson(
        lesson_slug: str,
        session: AsyncSession,
    ) -> None:
        """Delete an imported lesson and its dependent records."""
        await async_delete_one_record_by(
            Lesson,
            session,
            search_criteria=[Lesson.slug == lesson_slug],
        )

        return "Deleted lesson successfully"
