"""Client wrapper for S3 operations."""

from typing import Optional

import boto3
from botocore.exceptions import ClientError

from ..config.app import AppConfig
from ..middleware.exceptions import StorageError


class S3Client:
    """Client wrapper for S3 operations."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize S3 client.

        Args:
            config: Application configuration
        """
        self.config = config
        self.s3 = boto3.client("s3")
        self.bucket = config.pdf_bucket_name

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for uploading a file.

        Args:
            key: S3 object key
            expires_in: URL expiration time in seconds

        Returns:
            Presigned URL

        Raises:
            StorageError: If URL generation fails
        """
        try:
            url = self.s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": "application/pdf",
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise StorageError(
                f"Failed to generate presigned URL",
                code="generate_presigned_url_failed",
                details={"e": str(e)},
            )

    def upload_file(self, key: str, content: bytes) -> None:
        """Upload a file to S3.

        Args:
            key: S3 object key
            content: File content as bytes

        Raises:
            StorageError: If upload fails
        """
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType="application/pdf",
                ServerSideEncryption="AES256",
            )
        except ClientError as e:
            raise StorageError(
                f"Failed to upload file",
                code="upload_file_failed",
                details={"e": str(e)},
            )

    def get_object_url(self, key: str, expires_in: Optional[int] = None) -> str:
        """Get a URL for an S3 object.

        Args:
            key: S3 object key
            expires_in: URL expiration time in seconds (optional)

        Returns:
            Object URL

        Raises:
            StorageError: If URL generation fails
        """
        try:
            if expires_in:
                url = self.s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=expires_in,
                )
            else:
                url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
            return url
        except ClientError as e:
            raise StorageError(
                f"Failed to get object URL",
                code="get_object_url_failed",
                details={"e": str(e)},
            )

    def delete_object(self, key: str) -> None:
        """Delete an object from S3.

        Args:
            key: S3 object key

        Raises:
            StorageError: If deletion fails
        """
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise StorageError(
                f"Failed to delete object",
                code="delete_object_failed",
                details={"e": str(e)},
            )
