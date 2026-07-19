from fastapi import APIRouter, Depends, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.feedback.schemas import (
    FeedbackCreate,
    FeedbackPaginationFilter,
    FeedbackResponse,
    FeedbackResponseMetadata,
    FeedbackUpdate,
    PaginatedFeedbackResponse,
)
from app.features.feedback.service import FeedbackService


router = APIRouter()


@router.get(
    "",
    response_model=PaginatedFeedbackResponse,
    summary="Get all feedbacks",
)
async def get_all_feedbacks(
    request: Request,
    filters: FeedbackPaginationFilter = Depends(),
    session: AsyncSession = Depends(get_session),
) -> PaginatedFeedbackResponse:
    """Return the authenticated user's paginated feedback."""
    feedbacks, total, pages = await FeedbackService.get_all_feedbacks(
        session,
        filters,
        request,
    )
    return PaginatedFeedbackResponse(
        feedbacks=feedbacks,
        metadata=FeedbackResponseMetadata(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        ),
    )


@router.get(
    "/{feedback_id}",
    response_model=FeedbackResponse,
    summary="Get feedback by ID",
)
async def get_one_feedback(
    feedback_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    """Return feedback owned by the authenticated user."""
    return await FeedbackService.get_one_feedback(feedback_id, session, request)


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create feedback",
)
async def create_feedback(
    feedback_in: FeedbackCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    """Create feedback for the authenticated user."""
    return await FeedbackService.create_feedback(feedback_in, request, session)


@router.put(
    "/{feedback_id}",
    response_model=FeedbackResponse,
    summary="Update feedback",
)
async def update_feedback(
    feedback_id: int,
    feedback_in: FeedbackUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    """Update feedback owned by the authenticated user."""
    return await FeedbackService.update_feedback(
        feedback_id,
        feedback_in,
        request,
        session,
    )
