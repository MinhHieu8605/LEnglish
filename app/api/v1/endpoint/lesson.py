from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.lesson.schemas import (
    LessonListResponse,
    LessonDetailResponse,
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
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    return await LessonService.list_lessons(page, page_size, session)


@router.post(
    "/import/youtube",
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
    "/{lesson_slug}",
    response_model=LessonDetailResponse,
    summary="Get lesson details with timed subtitles",
)
async def get_lesson_detail(
    lesson_slug: str,
    session: AsyncSession = Depends(get_session),
):
    return await LessonService.get_detail(lesson_slug, session)


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
