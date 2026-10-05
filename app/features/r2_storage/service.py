import os
from typing import Optional
from urllib.parse import urlparse

import aioboto3
from botocore.config import Config

from app.config.settings import R2StorageConfig

r2_config = R2StorageConfig()


class R2StorageService(object):
    """Cloudflare R2 Storage Service Class."""

    def __init__(self) -> None:
        self.session = aioboto3.Session()

    def _client_kwargs(self) -> dict:
        """Return the keyword arguments for creating an R2 client."""
        return {
            "service_name": "s3",
            "aws_access_key_id": r2_config.access_key_id,
            "aws_secret_access_key": r2_config.secret_access_key,
            "endpoint_url": r2_config.endpoint_url,
            "region_name": "auto",
            "config": Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        }

    async def upload_file(
        self, file_path: str, object_name: str, content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to R2 storage.

        Args:
            file_path (str): The local path to the file to be uploaded.
            object_name (str): The name of the object in R2 storage.
            content_type (Optional[str]): The MIME type of the file.

        Returns:
            str: The URL of the uploaded file in R2 storage.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        async with self.session.client(**self._client_kwargs()) as client:
            await client.upload_file(
                file_path, r2_config.bucket_name, object_name, extra_args
            )

        return f"r2://{r2_config.bucket_name}/{object_name}"

    async def generate_signed_url(
        self,
        storage_uri: str,
    ) -> str:
        """
        Generate a signed URL for accessing a file in R2 storage.

        Args:
            storage_uri (str): The URI of the file in R2 storage.

        Returns:
            str: A signed URL for accessing the file.
        """
        parsed_uri = urlparse(storage_uri)
        if parsed_uri.scheme != "r2":
            raise ValueError(
                f"Invalid storage URI scheme: {parsed_uri.scheme}. Expected 'r2'."
            )

        if parsed_uri.netloc != r2_config.bucket_name:
            raise ValueError(
                f"Invalid bucket name in storage URI: {parsed_uri.netloc}. Expected '{r2_config.bucket_name}'."
            )

        # Extract the object name from the storage URI
        object_name = parsed_uri.path.lstrip("/")  # Remove leading slash

        async with self.session.client(**self._client_kwargs()) as client:
            signed_url = await client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": r2_config.bucket_name,
                    "Key": object_name,
                },
                ExpiresIn=r2_config.signed_url_expiration_seconds,
            )

        return signed_url
