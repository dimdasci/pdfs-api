"""Client wrapper for S3 operations."""

from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from ..config.app import AppConfig
from ..middleware.exceptions import StorageError
from ..middleware.logging import logger


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

    def download_file(self, bucket_name: str, object_key: str, file_path: str) -> None:
        """Download a file from S3.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            file_path: Local file path to save the downloaded file

        Raises:
            StorageError: If download fails
        """
        try:
            self.s3.download_file(bucket_name, object_key, file_path)
        except ClientError as e:
            raise StorageError(
                "Failed to download file",
                code="download_file_failed",
                details={"e": str(e)},
            )

    def sync_directory(self, local_dir: Path, s3_prefix: str) -> None:
        """Sync local directory to S3 bucket, similar to 'aws s3 sync' command.

        Args:
            local_dir: Local directory path
            s3_prefix: S3 prefix (folder path in bucket)

        Raises:
            StorageError: If sync operation fails
        """
        try:
            # Find all matching files in the local directory
            files_found = 0
            files_uploaded = 0

            for filepath in local_dir.rglob("*"):
                if not filepath.is_file() or not filepath.name.endswith(".png"):
                    continue

                files_found += 1

                # Calculate relative path from base directory
                rel_path = filepath.relative_to(local_dir)
                s3_key = f"{s3_prefix.rstrip('/')}/{rel_path.as_posix()}"

                # Upload file with appropriate content type and metadata
                with open(filepath, "rb") as f:
                    response = self.s3.put_object(
                        Bucket=self.bucket,
                        Key=s3_key,
                        Body=f,
                        ContentType="image/png",
                        Metadata={"generated": "true"},
                    )

                # Verify upload was successful by checking response
                if response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 200:
                    files_uploaded += 1
                else:
                    logger.error(
                        f"Failed to upload {rel_path}",
                        extra={
                            "status_code": response.get("ResponseMetadata", {}).get(
                                "HTTPStatusCode"
                            )
                        },
                    )

            if files_found == 0:
                logger.warning(f"No files found in {local_dir}")
            else:
                logger.debug(
                    f"Sync completed",
                    extra={
                        "files_found": files_found,
                        "files_uploaded": files_uploaded,
                        "s3_prefix": s3_prefix,
                    },
                )

            if files_uploaded != files_found:
                raise StorageError(
                    f"Not all files were uploaded successfully",
                    code="sync_partial_failure",
                    details={
                        "files_found": files_found,
                        "files_uploaded": files_uploaded,
                    },
                )

        except (OSError, ClientError) as e:
            raise StorageError(
                "Failed to sync directory to S3",
                code="sync_directory_failed",
                details={"e": str(e)},
            )
