from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.utils.constants import FeedbackStatus, FeedbackType, SortOrder


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
    description: Optional[str] = None
    user_attachments: Optional[List[str]] = None


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
        user_email (str): The email of the user providing feedback.
        type (str): The type of feedback (e.g., "bug", "feature request").
        title (str): The title of the feedback.
        description (Optional[str]): An optional detailed description of the feedback.
        status (Optional[str]): The status of the feedback (e.g., "new", "in progress", "resolved").
        user_attachments (Optional[List[str]]): A list of attachments provided by the user.
        response (Optional[str]): An optional response to the feedback.
        response_attachments (Optional[List[str]]): A list of attachments provided in the response.
        response_at (Optional[datetime]): The timestamp of when the response was provided.
        created_time (datetime): The timestamp of when the feedback was created.
    """

    id: int
    user_id: int
    user_email: Optional[str] = None
    type: FeedbackType
    title: str
    description: Optional[str] = None
    status: Optional[FeedbackStatus] = None
    user_attachments: Optional[List[str]] = None
    response: Optional[str] = None
    response_attachments: Optional[List[str]] = None
    response_at: Optional[datetime] = None
    created_time: datetime


class FeedbackListItemResponse(BaseModel):
    """
    Schema for feedback list item response.

    Atributes:
        id (int): The ID of the feedback.
        user_email (str): The email of the user providing feedback.
        type (str): The type of feedback (e.g., "bug", "feature request").
        title (str): The title of the feedback.
        status (Optional[str]): The status of the feedback (e.g., "new", "in progress", "resolved").
        created_time (datetime): The timestamp of when the feedback was created.
    """

    id: int
    user_email: str
    type: FeedbackType
    title: str
    status: Optional[FeedbackStatus] = None
    created_time: datetime


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
    status: Optional[FeedbackStatus] = None
    keyword: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    sort_by: Optional[str] = "created_time"
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


class ResponseFeedback(BaseModel):
    """
    Schema for responding to feedback.

    Atributes:
        response (str): The response to the feedback.
        response_attachments (Optional[List[str]]): A list of attachments provided in the response.
    """
    status: Optional[FeedbackStatus] = None
    response: Optional[str] = None 
    response_attachments: Optional[List[str]] = None


class FeedbackAttachmentUploadResponse(BaseModel):
    """
    Schema for feedback attachment upload response.

    Atributes:
        file_name (str): The name of the attachment file.
        local_path (str): The local path where the attachment is stored.
    """
    file_name: str = Field(serializer_alias="filename")
    local_path: str = Field(serializer_alias="localPath")


class FeedbackDeleteResponse(BaseModel):
    """
    Schema for feedback deletion response.

    Atributes:
        deleted_ids (list[int]): A list of the IDs of the deleted feedback items.
        deleted_count (int): The number of feedback items that were deleted.
    """
    deleted_ids: list[int]
    deleted_count: int


class FeedbackBulkDeleteRequest(BaseModel):
    """
    Schema for bulk feedback deletion request.

    Atributes:
        feedback_ids (List[int]): A list of feedback IDs to be deleted.
    """
    feedback_ids: List[int] = Field(..., min_items=1, max_items=100)
