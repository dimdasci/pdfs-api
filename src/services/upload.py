"""Service for document upload operations."""

from typing import Tuple
from uuid import uuid4

import requests

from ..clients.dynamodb import DynamoDBClient
from ..clients.s3 import S3Client
from ..config.app import AppConfig
from ..middleware.exceptions import (
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    StorageError,
)
from ..models.domain import Document, DocumentSource, ProcessingStatus
from ..models.storage.document_record import DocumentRecord


class UploadService:
    """Service for document upload operations."""

    def __init__(
        self, config: AppConfig, dynamodb_client: DynamoDBClient, s3_client: S3Client
    ) -> None:
        """Initialize upload service.

        Args:
            config: Application configuration
            dynamodb_client: DynamoDB client
            s3_client: S3 client
        """
        self.config = config
        self.dynamodb_client = dynamodb_client
        self.s3_client = s3_client

    def generate_document_id_key(self, user_id: str) -> Tuple[str, str]:
        """Generate a unique document ID and key.

        Returns:
            Document ID
            Key
        """
        document_id = f"doc_{uuid4().hex[:8]}"
        key = f"{user_id}/{document_id}/original.pdf"
        return document_id, key

    def upload_from_file(
        self, user_id: str, document_name: str, file_content: bytes
    ) -> str:
        """Upload a document from file content.
        Saves to S3 first, then creates the DynamoDB record.

        Args:
            user_id: ID of the user uploading the document
            document_name: Name of the document
            file_content: PDF file content as bytes

        Returns:
            Document ID

        Raises:
            StorageError: If S3 upload or DynamoDB write fails
            DocumentAlreadyExistsError: If the document record already exists
        """
        document_id, key = self.generate_document_id_key(user_id)

        try:
            # 1. Upload to S3 first
            self.s3_client.upload_file(key, file_content)

            # 2. If S3 upload succeeds, create and save DynamoDB record
            try:
                document = Document(
                    id=document_id,
                    user_id=user_id,
                    name=document_name,
                    source=DocumentSource.FILE,
                    source_url=None,
                    status=ProcessingStatus.PROCESSING,
                )
                record = DocumentRecord.from_domain(document)
                self.dynamodb_client.put_item(record.to_dynamo())

                return document_id
            except DocumentAlreadyExistsError as db_exc:
                # Handle the unlikely case where the generated ID collides
                # and the record already exists after S3 upload succeeded.
                # Consider logging this and potentially trying to delete the orphaned S3 object.
                # For now, re-raise the specific error.
                raise db_exc
            except Exception as db_exc:
                # Handle generic DB errors after successful S3 upload
                # Log, potentially try to delete orphaned S3 object
                raise StorageError(
                    f"DynamoDB write failed after successful S3 upload for {key}",
                    code="dynamodb_write_failed",
                    details={"db_exc": str(db_exc)},
                )

        except Exception as s3_exc:
            # Handle S3 upload errors
            raise StorageError(
                f"Failed to upload document to S3 ({key})",
                code="s3_upload_failed",
                details={"s3_exc": str(s3_exc)},
            )

    def upload_from_url(self, user_id: str, document_name: str, url: str) -> str:
        """Upload a document from a URL.
        Downloads from URL, saves to S3 first, then creates the DynamoDB record.

        Args:
            user_id: ID of the user uploading the document
            document_name: Name of the document
            url: URL to download the PDF from

        Returns:
            Document ID

        Raises:
            StorageError: If download, S3 upload, or DynamoDB write fails
            DocumentAlreadyExistsError: If the document record already exists
        """
        document_id, key = self.generate_document_id_key(user_id)

        try:
            # 1. Download from URL using requests instead of aiohttp
            response = requests.get(url)
            if response.status_code != 200:
                raise StorageError(
                    f"Failed to download PDF from URL ({url}): {response.status_code}",
                    code="url_download_failed",
                    details={"status": str(response)},
                )
            content = response.content

            # 2. Upload downloaded content to S3
            self.s3_client.upload_file(key, content)

            # 3. If S3 upload succeeds, create and save DynamoDB record
            try:
                document = Document(
                    id=document_id,
                    user_id=user_id,
                    name=document_name,
                    source=DocumentSource.URL,
                    source_url=url,
                    status=ProcessingStatus.PROCESSING,
                )
                record = DocumentRecord.from_domain(document)
                self.dynamodb_client.put_item(record.to_dynamo())

                return document_id
            except DocumentAlreadyExistsError as db_exc:
                raise db_exc  # Re-raise specific error
            except Exception as db_exc:
                raise StorageError(
                    f"DynamoDB write failed after successful S3 upload for {key}",
                    code="dynamodb_write_failed",
                    details={"db_exc": str(db_exc)},
                )

        except Exception as upload_exc:
            # Handle download or S3 errors
            raise StorageError(
                f"Failed to process document from URL ({url})",
                code="upload_failed",
                details={"upload_exc": str(upload_exc)},
            )

    def get_upload_status(self, user_id: str, document_id: str) -> ProcessingStatus:
        """Get the status of an upload.

        Args:
            user_id: ID of the user
            document_id: ID of the document

        Returns:
            Document status

        Raises:
            DocumentNotFoundError: If document not found
            StorageError: If status retrieval fails
        """
        try:
            # Get document record
            record_dict = self.dynamodb_client.get_item(
                pk=f"USER#{user_id}", sk=f"PDF#{document_id}"
            )
            if not record_dict:
                raise DocumentNotFoundError(
                    f"Document {document_id} not found for user {user_id}"
                )

            # Use the safe conversion method
            record = DocumentRecord.from_dynamo(record_dict)
            return record.status  # Return status from the validated record
        except DocumentNotFoundError:
            raise
        except Exception as e:
            raise StorageError(
                f"Failed to get upload status",
                code="get_upload_status_failed",
                details={"e": str(e)},
            )
