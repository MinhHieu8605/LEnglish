from fastapi import APIRouter, Depends, Query, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import get_session
from app.features.engagement.schemas import (
    EngagementActivityHistoryResponse,
    EngagementActivityRequest,
    EngagementActivityResponse,
    EngagementSummaryResponse,
)
from app.features.engagement.service import EngagementService
from app.utils.common import get_user_id_from_request


router = APIRouter()


@router.post("/activity", response_model=EngagementActivityResponse)
async def record_engagement_activity(
    request: Request,
    data: EngagementActivityRequest,
    session: AsyncSession = Depends(get_session),
) -> EngagementActivityResponse:
    """Record one batch of active study time for the current user."""
    user_id = get_user_id_from_request(request)
    return await EngagementService.record_activity(user_id, data, session)


@router.get("/summary", response_model=EngagementSummaryResponse)
async def get_engagement_summary(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> EngagementSummaryResponse:
    """Return today's learning totals and the current user's streaks."""
    user_id = get_user_id_from_request(request)
    return await EngagementService.get_summary(user_id, session)


@router.get("/activity", response_model=EngagementActivityHistoryResponse)
async def get_engagement_activity(
    request: Request,
    days: int = Query(default=90, ge=1, le=366),
    session: AsyncSession = Depends(get_session),
) -> EngagementActivityHistoryResponse:
    """Return daily learning activity for the requested period."""
    user_id = get_user_id_from_request(request)
    return await EngagementService.get_activity(user_id, days, session)
