import asyncio
import mimetypes
import os
import shutil
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, Request, UploadFile, status
from loguru import logger
from slugify import slugify
from sqlalchemy import or_
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config.settings import SystemConfig
from app.database.async_db import (
    async_bulk_update_records,
    async_create_record,
    async_get_many_records_by,
    async_get_one_record_by,
    async_get_one_record_by_id,
    async_get_paginated_records,
    async_update_one_record,
    transactional,
)
from app.features.email.service import email_service
from app.features.feedback.model import Feedback, FeedbackAttachment
from app.features.feedback.schemas import (
    FeedbackAttachmentUploadResponse,
    FeedbackCreate,
    FeedbackDeleteResponse,
    FeedbackListItemResponse,
    FeedbackPaginationFilter,
    FeedbackResponse,
    FeedbackUpdate,
    ResponseFeedback,
)
from app.features.r2_storage.service import R2StorageService
from app.features.user.model import User
from app.utils.common import (
    append_short_uuid_to_filename,
    get_user_email_from_request,
    get_user_id_from_request,
    get_user_role_from_request,
    page_size_to_offset_limit,
    remove_domain_from_email,
)
from app.utils.constants import (
    FeedbackAttachmentType,
    FeedbackFilter,
    FileConstants,
    FileMode,
    FileSizeLimit,
    FileType,
    Role,
    SortOrder,
)
from app.utils.email_constants import (
    BODY_NOTI_ADMIN_FEEDBACK,
    SUBJECT_NOTI_ADMIN_FEEDBACK,
)
from app.utils.util import check_user_id_match

r2_service = R2StorageService()


class FeedbackService(object):
    """
    FeedbackService class is responsible for handling feedback-related operations.

    Validates and stores attachments, manages feedback records, and supports
    administrator responses.
    """

    @staticmethod
    def _normalize_date_filters(
        value: Union[date, datetime], end_of_day: bool = False
    ) -> datetime:
        """
        Normalize a date or datetime value to a datetime object.

        Args:
            value (Union[date, datetime]): The date or datetime value to normalize.
            end_of_day (bool): Whether to set the time to the end of the day.

        Returns:
            datetime: The normalized datetime object.
        """
        if isinstance(value, datetime):
            normalized_value = value
        else:
            normalized_value = datetime.combine(value, time.min)

        if normalized_value.tzinfo is None:
            normalized_value = normalized_value.replace(tzinfo=timezone.utc)

        return (
            normalized_value.replace(hour=23, minute=59, second=59, microsecond=999999)
            if end_of_day
            else normalized_value
        )

    @staticmethod
    def _process_feedback_response(
        feedbacks, user_email: Dict[int, Optional[str]]
    ) -> list[FeedbackListItemResponse]:
        """
        Process feedback records and return a list of FeedbackListItemResponse.

        Args:
            feedback (Feedback): The feedback record to process.
            user_email (Dict[int, Optional[str]]): A dictionary mapping user IDs to their emails.

        Returns:
            list[FeedbackListItemResponse]: A list of processed feedback responses.
        """
        processed: List[FeedbackListItemResponse] = []
        for item in feedbacks:
            processed.append(
                FeedbackListItemResponse(
                    id=getattr(item, "id", None),
                    user_email=user_email.get(getattr(item, "user_id", None)),
                    type=getattr(item, "type", ""),
                    title=getattr(item, "title", ""),
                    status=getattr(item, "status", None),
                    created_time=getattr(item, "created_time", None),
                )
            )
        return processed

    @staticmethod
    async def _refresh_attachment_urls(
        urls: Optional[List[str]],
    ) -> Optional[List[str]]:
        """
        Refresh the attachment URLs by removing any query parameters.

        Args:
            urls (Optional[List[str]]): A list of attachment URLs.

        Returns:
            Optional[List[str]]: A list of refreshed attachment URLs without query parameters.
        """
        if not urls:
            return urls

        refreshed_urls = []
        for url in urls:
            try:
                refreshed_urls.append(await r2_service.generate_signed_url(url))
            except Exception as e:
                logger.error(f"Error refreshing URL {url}: {e}")
                refreshed_urls.append(url)

        return refreshed_urls

    @classmethod
    def check_file_type(cls, upload_files: List[UploadFile]) -> None:
        """
        Validate uploaded file extensions against the project's supported file types.

        Args:
            upload_files (List[UploadFile]): Uploaded files to validate.

        Raises:
            HTTPException: If any uploaded file has an unsupported extension.
        """
        allowed_extensions = {
            value.lower()
            for key, value in vars(FileType).items()
            if not key.startswith("_") and isinstance(value, str)
        }

        for upload_file in upload_files:
            _, file_extension = os.path.splitext(upload_file.filename or "")
            if file_extension.lower() not in allowed_extensions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File type is not allowed.",
                )

    @classmethod
    def check_file_size(cls, upload_files: List[UploadFile]) -> None:
        """
        Validate feedback attachment sizes by file extension.

        Args:
            upload_files (List[UploadFile]): The feedback files whose sizes must be
                checked.

        Raises:
            HTTPException: If an attachment exceeds its extension-specific size limit.
        """
        file_size_limits = {
            FileType.PNG: FileSizeLimit.SIZE_5MB,
            FileType.JPG: FileSizeLimit.SIZE_5MB,
            FileType.JPEG: FileSizeLimit.SIZE_5MB,
            FileType.TXT: FileSizeLimit.SIZE_1MB,
            FileType.MD: FileSizeLimit.SIZE_1MB,
            FileType.HTML: FileSizeLimit.SIZE_1MB,
        }

        default_limit = FileSizeLimit.SIZE_50MB

        for upload_file in upload_files:
            if not upload_file or not upload_file.filename:
                continue

            file_extension = os.path.splitext(upload_file.filename)[1].lower()
            max_file_size = file_size_limits.get(file_extension, default_limit)

            file_stream = upload_file.file
            current_position = file_stream.tell()
            file_stream.seek(0, os.SEEK_END)
            file_size = file_stream.tell()
            file_stream.seek(current_position)

            if file_size > max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=(
                        f"The file '{upload_file.filename}' exceeds the maximum "
                        f"allowed size of {max_file_size // FileSizeLimit._MB} MB."
                    ),
                )

    @classmethod
    async def save_feedback_file_locally(
        cls,
        upload_file: UploadFile,
        attachment_type: FeedbackAttachmentType,
        request: Request,
    ) -> FeedbackAttachmentUploadResponse:
        """
        Save a feedback file locally and return its relative path.

        Args:
            upload_file (UploadFile): The feedback attachment uploaded by the user.
            attachment_type (FeedbackAttachmentType): Whether the file belongs to user
                feedback or an administrator response.
            request (Request): The HTTP request containing the authenticated user's
                state.

        Returns:
            FeedbackAttachmentUploadResponse: The original filename and relative path of
                the saved attachment.

        Raises:
            HTTPException: If the file is missing, its type or size is invalid, or a
                non-administrator uploads a response attachment.
        """
        if not upload_file or not upload_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment file is required.",
            )

        if attachment_type == FeedbackAttachmentType.RESPONSE:
            role = get_user_role_from_request(request)
            if role != Role.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Admin can upload response attachments.",
                )

        cls.check_file_type([upload_file])
        cls.check_file_size([upload_file])

        _, file_local_path, _ = cls.save_uploaded_file(
            upload_file=upload_file,
            file_name=upload_file.filename,
            format_file_name=False,
        )

        return FeedbackAttachmentUploadResponse(
            file_name=upload_file.filename,
            local_path=os.path.relpath(file_local_path, "local_files").replace(
                "\\", "/"
            ),
        )

    @classmethod
    def _validate_feedback_file_path(cls, file_path: str) -> str:
        """
        Validate and resolve a path previously returned by local upload.

        Args:
            file_path (str): The relative path returned by the local feedback upload.

        Returns:
            str: The absolute path of an existing file inside the local upload
                directory.

        Raises:
            HTTPException: If the path leaves the local upload directory or does not
                name an existing file.
            ValueError: If the resolved path and upload directory are on different
                drives.
        """
        base_path = os.path.abspath("local_files")
        resolved_path = os.path.abspath(os.path.join("local_files", file_path))

        if os.path.commonpath(
            [base_path, resolved_path]
        ) != base_path or not os.path.isfile(resolved_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid feedback attachment path: {file_path}",
            )
        return resolved_path

    @classmethod
    async def process_feedback_attachment_paths(
        cls,
        feedback_id: int,
        file_paths: list[str],
        attachment_type: FeedbackAttachmentType,
        session: AsyncSession,
    ) -> tuple[list[str], list[str]]:
        """
        Upload local feedback files, persist metadata, and return email paths.

        Args:
            feedback_id (int): The identifier of the feedback to associate with the
                attachments.
            file_paths (list[str]): The relative paths of feedback attachments
                previously uploaded locally.
            attachment_type (FeedbackAttachmentType): Whether the file belongs to user
                feedback or an administrator response.
            session (AsyncSession): The database session used for record operations.

        Returns:
            tuple[list[str], list[str]]: The attachment storage URIs and local paths
                available for email attachments.

        Raises:
            HTTPException: If the feedback is missing or an attachment path is invalid.
        """

        feedback = await async_get_one_record_by_id(Feedback, feedback_id, session)

        if feedback is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with id {feedback_id} not found.",
            )

        attachment_column = (
            "user_attachments"
            if attachment_type == FeedbackAttachmentType.FEEDBACK
            else "response_attachments"
        )

        attachment_urls = list(getattr(feedback, attachment_column) or [])
        email_paths: list[str] = []

        for file_path in file_paths:
            local_path = cls._validate_feedback_file_path(file_path)
            file_name = os.path.basename(local_path)
            content_type = mimetypes.guess_type(file_name)[0]

            object_name = f"feedback/{feedback_id}/{file_name}"
            r2_uri = await r2_service.upload_file(
                file_path=local_path,
                object_name=object_name,
                content_type=content_type,
            )

            await async_create_record(
                FeedbackAttachment,
                {
                    "feedback_id": feedback_id,
                    "file_name": file_name,
                    "file_url": r2_uri,
                    "attachment_type": attachment_type.value,
                },
                session,
            )
            attachment_urls.append(r2_uri)
            email_paths.append(local_path)

        if attachment_urls:
            await async_update_one_record(
                Feedback,
                feedback_id,
                {attachment_column: attachment_urls},
                session,
            )
        return attachment_urls, email_paths

    @classmethod
    def save_uploaded_file(
        cls,
        upload_file: UploadFile,
        save_path: Union[str, None] = None,
        format_file_name: bool = True,
        file_name: str = "",
    ):
        """
        Save an uploaded file to the specified directory.

        Args:
            upload_file (UploadFile): The file uploaded by the user.
            save_path (str): Directory path to save the file.
            format_file_name (bool): Whether to format the file_name using
                slugify.
            file_name (str): Custom file_name to use if formatting is disabled.

        Returns:
            Tuple[str, int]: The full path to the saved file and its size in bytes.

        Raises:
            InvalidRequestException: If the formatted filename exceeds the maximum
                allowed length.
        """
        if save_path is None:
            save_path = "local_files"
        if format_file_name:
            file_name, file_extension = os.path.splitext(file_name)

            # Split the filename into name and extension
            # Process the filename with slugify (without changing the extension)
            file_name = slugify(file_name)

            # Validate the slugified filename length (excluding extension)
            if len(file_name) + len(file_extension) > FileConstants.MAX_FILENAME_LENGTH:
                raise ValueError(
                    "Filename is too long. Maximum length is "
                    f"{FileConstants.MAX_FILENAME_LENGTH} characters."
                )
            file_name = f"{file_name}{file_extension}"
        else:
            file_name, file_extension = os.path.splitext(file_name)
            file_name = f"{file_name}{file_extension}"

        unique_file_name = append_short_uuid_to_filename(file_name)
        file_local_path = os.path.join(save_path, unique_file_name)
        os.makedirs(save_path, exist_ok=True)

        with open(file_local_path, FileMode.WRITE_BINARY) as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        file_size = os.path.getsize(file_local_path)
        logger.info(f"Saved file {file_local_path}, size {file_size}")
        return unique_file_name, file_local_path, file_size

    @staticmethod
    def _append_env_prefix_subject(subject: str) -> str:
        """
        Append environment prefix to email subject if in non-production environment.

        Args:
            subject (str): The original email subject.

        Returns:
            str: The modified email subject with environment prefix if applicable.
        """
        if SystemConfig.ENV:
            return f"[{SystemConfig.ENV.upper()}] - {subject}"
        return subject

    @classmethod
    async def _send_email(
        cls,
        subject: str,
        body: str,
        recipients: list[str] = [],
        cc: list[str] = [],
        attachment_paths: list[str] = [],
    ) -> None:
        """
        Asynchronously send an email notification.

        Args:
            subject (str): The subject of the email.
            body (str): The body content of the email.
            recipients (list[str]): The list of recipient email addresses.
            cc (list[str]): The list of CC email addresses.
            attachment_paths (list[str]): Optional list of local file paths to attach.

        Returns:
            None
        """
        logger.info(
            f"Preparing to send email with subject '{subject}' "
            f"to recipients: {recipients} and cc: {cc}"
        )

        # subject = cls._append_env_prefix_subject(subject)

        email_payload: dict[str, Any] = {
            "to": ";".join(recipients),
            "cc": ";".join(cc),
            "subject": subject,
            "body": body,
        }

        attachments: list[dict[str, Any]] = []
        for file_path in attachment_paths:
            try:
                attachment = await email_service.create_attachment(file_path)
                attachments.append(attachment)
            except Exception as exc:
                logger.warning(
                    f"Failed to create attachment from path {file_path}: {exc}"
                )

        if attachments:
            email_payload["attachments"] = attachments

        try:
            await email_service.send_email(email_payload)
        except Exception as exc:
            logger.error(
                "Failed to send feedback notification email ({}): {}",
                type(exc).__name__,
                exc,
            )
        else:
            logger.info(
                f"Email with subject '{subject}' sent successfully "
                f"to recipients: {recipients} and cc: {cc}"
            )
        finally:
            for file_path in attachment_paths:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as exc:
                    logger.warning(
                        "Failed to delete temporary attachment file "
                        f"'{file_path}': {exc}"
                    )

    @staticmethod
    def _build_where_clause(filters: FeedbackPaginationFilter) -> list:
        """
        Build the WHERE clause for SQL queries based on provided filters.

        Args:
            filters (FeedbackPaginationFilter): The pagination and filtering criteria.
        Returns:
            list: A list of SQLAlchemy filter conditions.
        """
        where_clause = [Feedback.deleted.is_(False)]
        filters_dict = filters.model_dump(exclude_none=True, exclude_unset=True)
        for key, value in filters_dict.items():
            if key == FeedbackFilter.TYPE:
                where_clause.append(Feedback.type == value.value)
            elif key == FeedbackFilter.STATUS:
                where_clause.append(Feedback.status == value.value)
            elif key == FeedbackFilter.FROM_DATE:
                where_clause.append(
                    Feedback.created_time
                    >= FeedbackService._normalize_date_filters(value)
                )
            elif key == FeedbackFilter.TO_DATE:
                where_clause.append(
                    Feedback.created_time
                    <= FeedbackService._normalize_date_filters(value, end_of_day=True)
                )
            elif key == FeedbackFilter.KEYWORD:
                keyword = f"%{value}%"
                where_clause.append(
                    or_(
                        Feedback.title.ilike(keyword),
                        Feedback.user.has(User.email.ilike(keyword)),
                    )
                )
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
        where_clause = cls._build_where_clause(filters, request)
        if filters.page_size and filters.page:
            skip, limit = page_size_to_offset_limit(filters.page, filters.page_size)

        feedbacks, total = await async_get_paginated_records(
            Feedback,
            session,
            criteria=where_clause,
            skip=skip,
            page_size=limit,
            sort_by=filters.sort_by,
            sort_order=filters.sort_order or SortOrder.DESCEND,
        )

        pages = None
        if filters.page_size and filters.page:
            pages = -(-total // filters.page_size)

        user_ids = {item.user_id for item in feedbacks}
        user_emails: Dict[int, Optional[str]] = {}
        if user_ids:
            users = await async_get_many_records_by(
                User,
                [User.id.in_(user_ids)],
                session,
                raise_if_not_found=False,
            )
            user_emails = {user.id: user.email for user in users}

        data = cls._process_feedback_response(feedbacks, user_emails)

        return data, total, pages

    @classmethod
    async def get_one_feedback(
        cls,
        feedback_id: int,
        session: AsyncSession,
        request: Request,
    ) -> FeedbackResponse:
        """
        Get one feedback item owned by the current user.

        Args:
            feedback_id (int): The ID of the feedback to retrieve.
            session (AsyncSession): The database session.
            request (Request): The incoming request object.

        Returns:
            FeedbackResponse: The feedback response object for the specified feedback ID.
        """
        user_id = get_user_id_from_request(request)
        logger.info(f"Fetching feedback with ID {feedback_id} for user_id {user_id}")

        feedback = await async_get_one_record_by(
            Feedback,
            [Feedback.id == feedback_id, Feedback.deleted.is_(False)],
            session,
        )

        feedback_user = await async_get_one_record_by_id(
            User, feedback.user_id, session, raise_if_not_found=False
        )

        feedback_data = {
            col.name: getattr(feedback, col.name) for col in Feedback.__table__.columns
        }
        feedback_data["user_email"] = feedback_user.email if feedback_user else None
        feedback_data["user_attachments"] = await cls._refresh_attachment_urls(
            feedback_data.get("user_attachments")
        )
        feedback_data["response_attachments"] = await cls._refresh_attachment_urls(
            feedback_data.get("response_attachments")
        )
        return FeedbackResponse(**feedback_data)

    @classmethod
    @transactional()
    async def create_feedback(
        cls,
        feedback_in: FeedbackCreate,
        request: Request,
        session: AsyncSession,
        attachment_paths: List[str] = [],
    ) -> FeedbackResponse:
        """
        Create feedback for the current user.

        Args:
            feedback_in (FeedbackCreate): The feedback data to create.
            request (Request): The incoming request object.
            session (AsyncSession): The database session.

        Returns:
            FeedbackResponse: The created feedback record.
        """
        user_id = get_user_id_from_request(request)
        user_email = get_user_email_from_request(request)
        feedback_data = feedback_in.model_dump()
        feedback_data["user_id"] = user_id

        record = await async_create_record(
            Feedback,
            feedback_data,
            session,
        )

        attachemnt_paths = (
            await cls.process_feedback_attachment_paths(
                record.id,
                attachment_paths,
                FeedbackAttachmentType.FEEDBACK,
                session,
            )
        )[1]

        feedback_data = {
            col.name: getattr(record, col.name) for col in Feedback.__table__.columns
        }
        feedback_data["user_email"] = user_email

        logger.info(f"Created feedback with ID {record.id} for user_id {user_id}")
        response = FeedbackResponse(**feedback_data)

        # Send email notification to admin after the response has been validated.
        asyncio.create_task(
            cls._send_email(
                SUBJECT_NOTI_ADMIN_FEEDBACK,
                BODY_NOTI_ADMIN_FEEDBACK.format(
                    user=remove_domain_from_email(user_email),
                    type=getattr(feedback_in.type, "value", feedback_in.type),
                    title=feedback_in.title,
                    description=feedback_in.description,
                    user_attachments=getattr(feedback_in, "user_attachments", []),
                ),
                SystemConfig.ADMIN_EMAILS_FEEDBACK,
                [],
                attachment_paths=attachemnt_paths,
            )
        )
        return response

    @classmethod
    @transactional()
    async def update_feedback(
        cls,
        feedback_id: int,
        feedback_in: FeedbackUpdate,
        request: Request,
        session: AsyncSession,
    ) -> FeedbackResponse:
        """
        Update one feedback item owned by the current user.

        Args:
            feedback_id (int): The ID of the feedback to update.
            feedback_in (FeedbackUpdate): The updated feedback data.
            request (Request): The incoming request object.
            session (AsyncSession): The database session.

        Returns:
            FeedbackResponse: The updated feedback record.
        """
        user_id = get_user_id_from_request(request)
        feedback = await async_get_one_record_by(
            Feedback,
            [Feedback.id == feedback_id, Feedback.deleted.is_(False)],
            session,
        )
        check_user_id_match(feedback.user_id, request)

        record = await async_update_one_record(
            Feedback,
            feedback_id,
            feedback_in,
            session,
            search_criteria=[Feedback.id == feedback_id, Feedback.deleted.is_(False)],
        )
        logger.info(f"Updated feedback with ID {feedback_id} for user_id {user_id}")

        feedback_user = await async_get_one_record_by_id(
            User, record.user_id, session, raise_if_not_found=False
        )
        feedback_data = {
            col.name: getattr(record, col.name) for col in Feedback.__table__.columns
        }
        feedback_data["user_email"] = feedback_user.email if feedback_user else None
        feedback_data["user_attachments"] = await cls._refresh_attachment_urls(
            feedback_data.get("user_attachments")
        )
        feedback_data["response_attachments"] = await cls._refresh_attachment_urls(
            feedback_data.get("response_attachments")
        )
        return FeedbackResponse(**feedback_data)

    @classmethod
    @transactional()
    async def response_feedback(
        cls,
        feedback_id: int,
        feedback_in: ResponseFeedback,
        session: AsyncSession,
        attachment_paths: List[str] = [],
    ) -> FeedbackResponse:
        """
        Respond to one feedback item owned by the current user.

        Args:
            feedback_id (int): The ID of the feedback to respond to.
            feedback_in (FeedbackUpdate): The updated feedback data.
            session (AsyncSession): The database session.
            attachment_paths (List[str]): A list of paths to the attached files.

        Returns:
            FeedbackResponse: The updated feedback record.
        """
        feedback = await async_get_one_record_by_id(Feedback, feedback_id, session)

        if feedback is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with id {feedback_id} not found.",
            )

        _, processed_paths = await cls.process_feedback_attachment_paths(
            feedback_id,
            attachment_paths,
            FeedbackAttachmentType.RESPONSE,
            session,
        )

        record = await async_update_one_record(
            Feedback,
            feedback_id,
            feedback_in,
            session,
            extra_data={
                "response_at": datetime.now(timezone.utc),
            },
        )

        for attachment_path in processed_paths:
            try:
                if os.path.exists(attachment_path):
                    os.remove(attachment_path)
            except Exception as exc:
                logger.warning(
                    f"Failed to delete temporary attachment file '{attachment_path}': {exc}"
                )

        logger.info(f"Responded to feedback with ID {feedback_id}")

        feedback_data = {
            col.name: getattr(record, col.name) for col in Feedback.__table__.columns
        }
        feedback_user = await async_get_one_record_by_id(
            User, feedback.user_id, session, raise_if_not_found=False
        )
        feedback_data["user_email"] = feedback_user.email if feedback_user else None

        return FeedbackResponse(**feedback_data)

    @classmethod
    @transactional()
    async def delete_feedback(
        cls,
        feedback_id: int,
        session: AsyncSession,
    ) -> FeedbackDeleteResponse:
        """
        Delete one feedback item owned by the current user.

        Args:
            feedback_id (int): The ID of the feedback to delete.
            session (AsyncSession): The database session.
            request (Request): The incoming request object.

        Returns:
            FeedbackDeleteResponse: The response indicating the result of the deletion operation.
        """
        await async_get_one_record_by(
            Feedback,
            [Feedback.id == feedback_id, Feedback.deleted.is_(False)],
            session,
            not_found_msg=f"Feedback with id {feedback_id} not found.",
            raise_if_not_found=True,
        )

        await async_update_one_record(
            Feedback,
            feedback_id,
            {"deleted": True},
            session,
            search_criteria=[Feedback.id == feedback_id, Feedback.deleted.is_(False)],
        )
        logger.info(f"Deleted feedback with ID {feedback_id}")
        return FeedbackDeleteResponse(deleted_ids=[feedback_id], deleted_count=1)

    @classmethod
    @transactional()
    async def bulk_delete_feedback(
        cls,
        feedback_ids: List[int],
        session: AsyncSession,
    ) -> FeedbackDeleteResponse:
        """
        Bulk delete feedback items owned by the current user.

        Args:
            feedback_ids (List[int]): A list of feedback IDs to delete.
            session (AsyncSession): The database session.
            request (Request): The incoming request object.

        Returns:
            FeedbackDeleteResponse: The response indicating the result of the bulk deletion operation.
        """
        unique_feedback_ids = list(dict.fromkeys(feedback_ids))
        logger.info(
            f"Attempting to bulk delete feedback with IDs: {unique_feedback_ids}"
        )

        records = await async_get_many_records_by(
            Feedback,
            [Feedback.id.in_(unique_feedback_ids), Feedback.deleted.is_(False)],
            session,
            raise_if_not_found=True,
        )

        await async_bulk_update_records(
            Feedback,
            search_criteria=[
                Feedback.id.in_(unique_feedback_ids),
                Feedback.deleted.is_(False),
            ],
            data={"deleted": True},
            session=session,
        )

        deleted_ids = [record.id for record in records]

        logger.info(f"Successfully bulk deleted feedback with IDs: {deleted_ids}")

        return FeedbackDeleteResponse(
            deleted_ids=feedback_ids, deleted_count=len(deleted_ids)
        )
