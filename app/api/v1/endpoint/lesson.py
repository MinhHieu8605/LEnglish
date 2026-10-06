from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.lesson.schemas import (
    LessonDetailResponse,
    LessonListMeta,
    LessonListResponse,
    LessonPaginationFilter,
    LessonProgressRequest,
    LessonProgressResponse,
    LessonResumeResponse,
    LessonSessionRequest,
    LessonSessionResponse,
    LessonCompleteRequest,
    YouTubeLessonImportRequest,
)
from app.features.lesson.service import LessonService
from app.utils.common import get_user_id_from_request, get_user_role_from_request
from app.utils.constants import Role


router = APIRouter()


@router.get(
    "",
    response_model=LessonListResponse,
    summary="List imported video lessons",
)
async def list_lessons(
    filters: LessonPaginationFilter = Depends(),
    session: AsyncSession = Depends(get_session),
) -> LessonListResponse:
    lessons, total, pages = await LessonService.list_lessons(filters, session)
    return LessonListResponse(
        data=lessons,
        metadata=LessonListMeta(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        ),
    )


@router.post(
    "/from-youtube",
    response_model=LessonDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import a YouTube video and all available English captions",
)
async def import_youtube_lesson(
    request: Request,
    data: YouTubeLessonImportRequest,
    session: AsyncSession = Depends(get_session),
):
    if get_user_role_from_request(request) != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    user_id = get_user_id_from_request(request)
    return await LessonService.import_youtube(user_id, data, session)


@router.get(
    "/resume",
    response_model=LessonResumeResponse | None,
    summary="Get the most recently watched unfinished lesson",
)
async def get_lesson_resume(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = get_user_id_from_request(request)
    return await LessonService.get_resume(user_id, session)


@router.get(
    "/{lesson_slug}",
    response_model=LessonDetailResponse,
    summary="Get lesson details with timed subtitles",
)
async def get_lesson_detail(
    lesson_slug: str,
    session: AsyncSession = Depends(get_session),
):
    return await LessonService.get_detail(lesson_slug, session)


@router.get("/{lesson_slug}/progress", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await LessonService.get_progress(
        get_user_id_from_request(request), lesson_slug, session
    )


@router.put("/{lesson_slug}/progress", response_model=LessonProgressResponse)
async def save_lesson_progress(
    lesson_slug: str,
    data: LessonProgressRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await LessonService.save_progress(
        get_user_id_from_request(request), lesson_slug, data, session
    )


@router.post(
    "/{lesson_slug}/sessions",
    response_model=LessonSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_lesson_session(
    lesson_slug: str,
    data: LessonSessionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await LessonService.start_session(
        get_user_id_from_request(request), lesson_slug, data, session
    )


@router.post(
    "/complete",
    response_model=LessonSessionResponse,
)
async def complete_lesson_session(
    data: LessonCompleteRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await LessonService.complete_session(
        get_user_id_from_request(request), data.lesson_slug, data.session_id, session
    )


@router.delete(
    "/{lesson_slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an imported video lesson",
)
async def delete_lesson(
    lesson_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    if get_user_role_from_request(request) != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    await LessonService.delete_lesson(lesson_slug, session)
