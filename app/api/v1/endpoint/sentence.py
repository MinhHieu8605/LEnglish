from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.lesson.schemas import (
    LessonAnswerRequest,
    LessonAnswerResponse,
    LessonAnswerSubmitRequest,
)
from app.features.lesson.service import LessonService
from app.utils.common import get_user_id_from_request


router = APIRouter()


@router.post("/submit", response_model=LessonAnswerResponse)
async def submit_lesson_answer(
    data: LessonAnswerSubmitRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await LessonService.submit_answer(
        get_user_id_from_request(request),
        data.lesson_slug,
        data.session_id,
        LessonAnswerRequest(subtitle_id=data.subtitle_id, user_input=data.user_input),
        session,
    )
