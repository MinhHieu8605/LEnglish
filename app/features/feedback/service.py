from fastapi import Request
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.async_db import (
    async_create_record,
    async_get_one_record_by_id,
    async_get_paginated_records,
    async_update_one_record,
)
from app.features.feedback.model import Feedback
from app.features.feedback.schemas import (
    FeedbackCreate,
    FeedbackPaginationFilter,
    FeedbackResponse,
    FeedbackUpdate,
)
from app.utils.common import get_user_id_from_request, page_size_to_offset_limit
from app.utils.constants import SortOrder
from app.utils.util import check_user_id_match


class FeedbackService(object):
    """
    FeedbackService class is responsible for handling feedback-related operations.
    """

    @staticmethod
    def _build_where_clause(filters: FeedbackPaginationFilter, request: Request) -> list:
        """
        Build the WHERE clause for SQL queries based on provided filters.

        Args:
            filters (FeedbackPaginationFilter): The pagination and filtering criteria.
            request (Request): The incoming request object.

        Returns:
            list: A list of SQLAlchemy filter conditions.
        """
        where_clause = [Feedback.user_id == get_user_id_from_request(request)]
        filters_dict = filters.model_dump(exclude_none=True, exclude_unset=True)
        for key, value in filters_dict.items():
            if key == "type":
                where_clause.append(Feedback.type == value.value)
            elif key == "keyword":
                where_clause.append(Feedback.title.ilike(f"%{value}%"))
        return where_clause

    @classmethod
    async def get_all_feedbacks(
        cls,
        session: AsyncSession,
        filters: FeedbackPaginationFilter,
        request: Request,
    ) -> tuple[list[dict], int, int]:
        """
        Retrieve all feedbacks based on provided filters and pagination.

        Args:
            session (AsyncSession): The database session.
            filters (FeedbackPaginationFilter): The pagination and filtering criteria.
            request (Request): The incoming request object.

        Returns:
            tuple[list[dict], int, int]: A tuple of:
                - List of feedbacks matching the criteria.
                - Total count of feedbacks matching the criteria.
                - Total number of pages based on the page size.
        """
        user_id = get_user_id_from_request(request)
        where_clause = cls._build_where_clause(filters, request)
        page = filters.page or 1
        page_size = filters.page_size or 10
        skip, limit = page_size_to_offset_limit(page, page_size)

        feedbacks, total = await async_get_paginated_records(
            Feedback,
            session,
            criteria=where_clause,
            skip=skip,
            page_size=limit,
            sort_by=filters.sort_by,
            sort_order=filters.sort_order or SortOrder.DESCEND,
        )

        pages = -(-total // page_size) if total else 0
        data = [
            {
                column.name: getattr(feedback, column.name)
                for column in Feedback.__table__.columns
            }
            for feedback in feedbacks
        ]
        logger.info(f"Fetched {total} feedbacks for user_id {user_id}")
        return data, total, pages

    @staticmethod
    async def get_one_feedback(
        feedback_id: int,
        session: AsyncSession,
        request: Request,
    ) -> FeedbackResponse:
        """Return one feedback item owned by the current user."""
        user_id = get_user_id_from_request(request)
        logger.info(f"Fetching feedback with ID {feedback_id} for user_id {user_id}")

        feedback = await async_get_one_record_by_id(
            Feedback,
            feedback_id,
            session,
        )
        check_user_id_match(feedback.user_id, request)

        feedback_response = {
            col.name: getattr(feedback, col.name) for col in Feedback.__table__.columns
        }
        return FeedbackResponse(**feedback_response)

    @staticmethod
    async def create_feedback(
        feedback_in: FeedbackCreate,
        request: Request,
        session: AsyncSession,
    ) -> Feedback:
        """
        Create feedback for the current user.

        Args:
            feedback_in (FeedbackCreate): The feedback data to create.
            request (Request): The incoming request object.
            session (AsyncSession): The database session.

        Returns:
            Feedback: The created feedback record.
        """
        user_id = get_user_id_from_request(request)
        feedback_data = feedback_in.model_dump()

        record = await async_create_record(
            Feedback,
            feedback_data,
            session,
            extra_data={"user_id": user_id},
        )
        logger.info(f"Created feedback with ID {record.id} for user_id {user_id}")
        return record

    @classmethod
    async def update_feedback(
        cls,
        feedback_id: int,
        feedback_in: FeedbackUpdate,
        request: Request,
        session: AsyncSession,
    ) -> Feedback:
        """
        Update one feedback item owned by the current user.

        Args:
            feedback_id (int): The ID of the feedback to update.
            feedback_in (FeedbackUpdate): The updated feedback data.
            request (Request): The incoming request object.
            session (AsyncSession): The database session.

        Returns:
            Feedback: The updated feedback record.
        """
        feedback = await cls.get_one_feedback(feedback_id, session, request)
        return await async_update_one_record(
            Feedback,
            feedback.id,
            feedback_in,
            session,
        )
