from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.feedback.schemas import (
    FeedbackAttachmentUploadResponse,
    FeedbackBulkDeleteRequest,
    FeedbackCreate,
    FeedbackDeleteResponse,
    FeedbackPaginationFilter,
    FeedbackResponse,
    FeedbackResponseMetadata,
    FeedbackUpdate,
    PaginatedFeedbackResponse,
    ResponseFeedback,
)
from app.features.feedback.service import FeedbackService
from app.utils.constants import FeedbackAttachmentType, FeedbackStatus, FeedbackType, Role
from app.utils.permission.enforcer import Policy, PolicyEnforcer


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
    "/attachments", response_model=FeedbackAttachmentUploadResponse
)
async def upload_feedback_attachment(
    request: Request,
    attachment_type: FeedbackAttachmentType = Form(...),
    file: UploadFile = File(...),
) -> FeedbackAttachmentUploadResponse:
    """Generate a pre-signed URL for uploading feedback attachments."""
    return await FeedbackService.save_feedback_file_locally(file, attachment_type, request  )


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create feedback",
)
async def create_feedback(
    request: Request,
    type: FeedbackType = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    attachment_paths: Optional[list[str]] = Form(None),
    session: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    """Create feedback for the authenticated user."""
    payload = FeedbackCreate(
        type=type,
        title=title,
        description=description,
        user_attachments=attachment_paths,
    )
    return await FeedbackService.create_feedback(
        payload,
        request,
        session,
        attachment_paths=attachment_paths or [],
    )


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


@router.post(
    "/{feedback_id}/response",
)
@PolicyEnforcer.required(Policy.role(Role.ADMIN))
async def response_feedback(
    feedback_id: int,
    request: Request,
    status: Optional[FeedbackStatus] = Form(None),
    response: str = Form(...),
    attachment_paths: Optional[list[str]] = Form(None),
    session: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    """Respond to feedback owned by the authenticated user."""
    payload = ResponseFeedback(
        status=status,
        response=response,
    )
    return await FeedbackService.response_feedback(
        feedback_id,
        payload,
        session,
        attachment_paths=attachment_paths or [],
    )


@router.delete(
    "/{feedback_id}",
    response_model=FeedbackDeleteResponse,
)
@PolicyEnforcer.required(Policy.role(Role.ADMIN))
async def delete_feedback(
    feedback_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> FeedbackDeleteResponse:
    """Delete feedback owned by the authenticated user."""
    return await FeedbackService.delete_feedback(
        feedback_id,
        session,
    )


@router.delete("", response_model=FeedbackDeleteResponse)
@PolicyEnforcer.required(Policy.role(Role.ADMIN))
async def bulk_delete_feedback(
    feedback_ids: FeedbackBulkDeleteRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> FeedbackDeleteResponse:
    """Bulk delete feedback owned by the authenticated user."""
    return await FeedbackService.bulk_delete_feedback(
        feedback_ids.feedback_ids,
        session,
    )
