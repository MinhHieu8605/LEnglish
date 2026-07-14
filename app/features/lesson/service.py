import asyncio
import html
import math
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from youtube_transcript_api import YouTubeTranscriptApi

from app.features.lesson.model import Category, Lesson, Subtitle
from app.features.lesson.schemas import (
    LessonListMeta,
    LessonListResponse,
    LessonPlayerResponse,
    LessonSummaryResponse,
    SubtitlePlayerResponse,
    YouTubeLessonImportRequest,
)
from app.utils.constants import ContentStatus


_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
_SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]*$")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_NON_SPEECH_RE = re.compile(r"^\[[^\]]+\]$")
_MAX_SEGMENT_SECONDS = 12.0
_MAX_SEGMENT_WORDS = 24


def _extract_youtube_video_id(video_url: str) -> str:
    """Extract a video ID while rejecting non-YouTube hosts."""
    parsed = urlparse(video_url)
    host = parsed.netloc.lower()
    if parsed.scheme not in {"http", "https"} or host not in _YOUTUBE_HOSTS:
        raise ValueError("Only YouTube video URLs are supported")

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        path_parts = [part for part in parsed.path.split("/") if part]
        video_id = (
            path_parts[1]
            if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts", "live"}
            else ""
        )

    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id):
        raise ValueError("Invalid YouTube video URL")
    return video_id


def _normalize_caption_text(text: str) -> str:
    normalized = html.unescape(_HTML_TAG_RE.sub("", text or ""))
    return _SPACE_RE.sub(" ", normalized.replace("\n", " ")).strip()


def _group_transcript(raw_snippets: list[dict]) -> list[dict]:
    """Merge caption cues into readable timed sentences."""
    segments: list[dict] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            current["content_en"] = " ".join(current.pop("parts"))
            segments.append(current)
            current = None

    for snippet in raw_snippets:
        text = _normalize_caption_text(str(snippet.get("text", "")))
        if not text or _NON_SPEECH_RE.fullmatch(text):
            continue

        start_seconds = max(float(snippet.get("start", 0)), 0)
        duration_seconds = max(float(snippet.get("duration", 0)), 0.01)
        end_seconds = start_seconds + duration_seconds

        if current is None or start_seconds - current["end_seconds"] > 1.5:
            flush()
            current = {
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "parts": [text],
            }
        else:
            current["parts"].append(text)
            current["end_seconds"] = max(current["end_seconds"], end_seconds)

        combined_text = " ".join(current["parts"])
        segment_duration = current["end_seconds"] - current["start_seconds"]
        if (
            _SENTENCE_END_RE.search(combined_text)
            or segment_duration >= _MAX_SEGMENT_SECONDS
            or len(combined_text.split()) >= _MAX_SEGMENT_WORDS
        ):
            flush()

    flush()
    return segments


def _translation_for_segment(
    translated_snippets: list[dict],
    start_seconds: float,
    end_seconds: float,
) -> str | None:
    parts = []
    for snippet in translated_snippets:
        snippet_start = float(snippet.get("start", 0))
        snippet_end = snippet_start + max(float(snippet.get("duration", 0)), 0.01)
        if snippet_end > start_seconds and snippet_start < end_seconds:
            text = _normalize_caption_text(str(snippet.get("text", "")))
            if text and (not parts or parts[-1] != text):
                parts.append(text)
    return " ".join(parts) or None


def _fetch_transcript(video_id: str, translate_to_vi: bool) -> tuple[list, list, str]:
    transcript_list = YouTubeTranscriptApi().list(video_id)
    transcript = transcript_list.find_transcript(["en", "en-US", "en-GB"])
    english_snippets = transcript.fetch().to_raw_data()
    translated_snippets = []
    if translate_to_vi and transcript.is_translatable:
        try:
            translated_snippets = transcript.translate("vi").fetch().to_raw_data()
        except Exception as error:
            logger.warning(f"Vietnamese transcript translation unavailable: {error}")
    return english_snippets, translated_snippets, transcript.language_code


async def _fetch_youtube_metadata(video_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://www.youtube.com/oembed",
                params={"url": video_url, "format": "json"},
            )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as error:
        logger.error(f"Unable to fetch YouTube metadata: {error}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch YouTube video metadata",
        )


async def _load_youtube_lesson_data(
    video_url: str,
    translate_to_vi: bool,
) -> tuple[str, dict, list[dict]]:
    try:
        video_id = _extract_youtube_video_id(video_url)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )

    metadata, transcript_result = await asyncio.gather(
        _fetch_youtube_metadata(video_url),
        asyncio.to_thread(_fetch_transcript, video_id, translate_to_vi),
        return_exceptions=True,
    )
    if isinstance(metadata, Exception):
        raise metadata
    if isinstance(transcript_result, Exception):
        logger.error(f"Unable to fetch YouTube transcript: {transcript_result}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="English captions are unavailable for this YouTube video",
        )

    english_snippets, translated_snippets, _ = transcript_result
    segments = _group_transcript(english_snippets)
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="YouTube transcript contains no usable sentences",
        )

    for segment in segments:
        segment["translation_vi"] = _translation_for_segment(
            translated_snippets,
            segment["start_seconds"],
            segment["end_seconds"],
        )
    return video_id, metadata, segments


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized.lower())).strip("-")


def _build_lesson_player_response(
    lesson: Lesson,
    subtitles: list[Subtitle],
) -> LessonPlayerResponse:
    """Build a player payload containing every subtitle in timeline order."""
    ordered_subtitles = sorted(subtitles, key=lambda item: (item.sequence, item.start_ms))
    subtitle_responses = [
        SubtitlePlayerResponse(
            id=subtitle.id,
            sequence=subtitle.sequence,
            start_ms=subtitle.start_ms,
            end_ms=subtitle.end_ms,
            content_en=subtitle.content_en,
            translation_vi=subtitle.translation_vi,
        )
        for subtitle in ordered_subtitles
    ]
    return LessonPlayerResponse(
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


class LessonService(object):
    """Import and read video lessons with complete timed transcripts."""

    @staticmethod
    async def get_player(
        lesson_slug: str,
        session: AsyncSession,
    ) -> LessonPlayerResponse:
        lesson = (
            await session.exec(
                select(Lesson).where(
                    Lesson.slug == lesson_slug,
                    Lesson.status == ContentStatus.PUBLISHED.value,
                )
            )
        ).first()
        if lesson is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found",
            )

        subtitles = (
            await session.exec(
                select(Subtitle)
                .where(Subtitle.lesson_id == lesson.id)
                .order_by(Subtitle.sequence.asc(), Subtitle.start_ms.asc())
            )
        ).all()
        return _build_lesson_player_response(lesson, subtitles)

    @staticmethod
    async def list_lessons(
        page: int,
        page_size: int,
        session: AsyncSession,
    ) -> LessonListResponse:
        published_condition = Lesson.status == ContentStatus.PUBLISHED.value
        total = (
            await session.exec(
                select(func.count(Lesson.id)).where(published_condition)
            )
        ).one()

        rows = (
            await session.exec(
                select(Lesson, func.count(Subtitle.id))
                .outerjoin(Subtitle, Subtitle.lesson_id == Lesson.id)
                .where(published_condition)
                .group_by(Lesson.id)
                .order_by(Lesson.published_at.desc(), Lesson.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return LessonListResponse(
            data=[
                _build_lesson_summary_response(lesson, subtitle_count)
                for lesson, subtitle_count in rows
            ],
            meta=LessonListMeta(
                total=total,
                page=page,
                page_size=page_size,
                pages=math.ceil(total / page_size) if total else 0,
            ),
        )

    @staticmethod
    async def import_youtube(
        user_id: int,
        data: YouTubeLessonImportRequest,
        session: AsyncSession,
    ) -> LessonPlayerResponse:
        """Import one YouTube video and persist its complete English transcript."""
        video_id, metadata, segments = await _load_youtube_lesson_data(
            data.video_url,
            data.translate_to_vi,
        )

        existing_lesson = (
            await session.exec(
                select(Lesson).where(
                    Lesson.video_provider == "youtube",
                    Lesson.video_id == video_id,
                )
            )
        ).first()
        if existing_lesson is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This YouTube video has already been imported",
            )

        if data.category_id is not None:
            category = await session.get(Category, data.category_id)
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found",
                )

        title = data.title or _normalize_caption_text(str(metadata.get("title", "")))
        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The YouTube video has no usable title",
            )

        slug = (_slugify(title) or f"youtube-{video_id}")[:255]
        slug_exists = (
            await session.exec(select(Lesson.id).where(Lesson.slug == slug))
        ).first()
        if slug_exists is not None:
            slug = f"{slug[:244].rstrip('-')}-{video_id}"

        lesson = Lesson(
            category_id=data.category_id,
            title=title,
            slug=slug,
            description=data.description,
            video_provider="youtube",
            video_id=video_id,
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            thumbnail_url=metadata.get("thumbnail_url"),
            duration_seconds=math.ceil(segments[-1]["end_seconds"]),
            difficulty=data.difficulty.value,
            status=ContentStatus.PUBLISHED.value,
            views_count=0,
            published_at=datetime.now(timezone.utc),
            created_by=user_id,
            updated_by=user_id,
        )
        subtitles = []
        for sequence, segment in enumerate(segments, start=1):
            start_ms = round(segment["start_seconds"] * 1000)
            end_ms = max(round(segment["end_seconds"] * 1000), start_ms + 1)
            subtitles.append(
                Subtitle(
                    lesson=lesson,
                    sequence=sequence,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    content_en=segment["content_en"],
                    translation_vi=segment["translation_vi"],
                )
            )

        try:
            session.add(lesson)
            session.add_all(subtitles)
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            logger.warning(f"YouTube lesson import conflict: {error}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The lesson conflicts with an existing record",
            )

        return _build_lesson_player_response(lesson, subtitles)
