from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.utils.constants import FeedbackType, SortOrder


class FeedbackCreate(BaseModel):
    """
    Schema for creating feedback.

    Atributes:
        user_id (int): The ID of the user providing feedback.
        type (str): The type of feedback (e.g., "bug", "feature request").
        title (str): The title of the feedback.
        description (Optional[str]): An optional detailed description of the feedback.
    """
    type: FeedbackType
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)


class FeedbackUpdate(BaseModel):
    """
    Schema for updating feedback.

    Atributes:
        type (Optional[str]): The updated type of feedback (e.g., "bug", "feature request").
        title (Optional[str]): The updated title of the feedback.
        description (Optional[str]): An optional updated detailed description of the feedback.
    """
    type: Optional[FeedbackType] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)


class FeedbackResponse(BaseModel):
    """
    Schema for feedback response.

    Atributes:
        id (int): The ID of the feedback.
        user_id (int): The ID of the user providing feedback.
        type (str): The type of feedback (e.g., "bug", "feature request").
        title (str): The title of the feedback.
        description (Optional[str]): An optional detailed description of the feedback.
    """
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    type: FeedbackType
    title: str
    description: Optional[str] = None
    created_time: datetime
    updated_time: datetime


class FeedbackPaginationFilter(BaseModel):
    """
    Schema for filtering and paginating feedback.

    Atributes:
        page: The page number for pagination (default is 1).
        page_size: The number of items per page for pagination (default is 10).
        type: The type of feedback to filter by.
        keyword: A keyword to search for in the feedback title or description.
        sort_by: The field to sort the feedback by (default is "created_time").
        sort_order: The order to sort the feedback (default is "desc").
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    type: Optional[FeedbackType] = None
    keyword: Optional[str] = None
    sort_by: Literal["created_time", "updated_time", "title", "type"] = "created_time"
    sort_order: SortOrder = SortOrder.DESCEND

class FeedbackResponseMetadata(BaseModel):
    """
    Schema for feedback response metadata.

    Atributes:
        total (int): The total number of feedback items.
        page (int): The current page number.
        page_size (int): The number of items per page.
        pages (int): The total number of pages.
    """
    total: int
    page: Optional[int] = None
    page_size: Optional[int] = None
    pages: Optional[int] = None


class PaginatedFeedbackResponse(BaseModel):
    """
    Schema for paginated feedback response.

    Atributes:
        metadata (FeedbackResponseMetadata): Metadata about the paginated response.
        feedbacks (List[FeedbackResponse]): A list of feedback responses.
    """
    feedbacks: List[FeedbackResponse]
    metadata: FeedbackResponseMetadata
