"""Service for document upload operations."""

from typing import Tuple

import requests

from ..clients.s3 import S3Client
from ..config.app import AppConfig
from ..middleware.exceptions import (
    DocumentAlreadyExistsError,
    S3UploadError,
    URLDownloadError,
    DatabaseWriteError,
)
from ..models.domain import Document, DocumentSource, ProcessingStatus
from ..repositories.document import generate_document_id, generate_document_id_from_content, generate_document_id_from_url
from ..repositories.dynamodb_document import DynamoDBDocumentRepository


class UploadService:
    """Service for document upload operations."""

    def __init__(
        self, config: AppConfig, document_repository: DynamoDBDocumentRepository, s3_client: S3Client
    ) -> None:
        """Initialize upload service.

        Args:
            config: Application configuration
            document_repository: Repository for document operations
            s3_client: S3 client for file storage
        """
        self.config = config
        self.document_repository = document_repository
        self.s3_client = s3_client

    def generate_document_id_key(self, user_id: str, content: bytes = None, url: str = None) -> Tuple[str, str]:
        """Generate a document ID and key based on content hash or URL.

        Args:
            user_id: ID of the user uploading the document
            content: Optional file content bytes
            url: Optional source URL

        Returns:
            Document ID
            Key
        """
        if content is not None:
            document_id = generate_document_id_from_content(content)
        elif url is not None:
            document_id = generate_document_id_from_url(url)
        else:
            document_id = generate_document_id()

        key = f"{user_id}/{document_id}/original.pdf"
        return document_id, key

    def upload_from_file(
        self, user_id: str, document_name: str, file_content: bytes
    ) -> str:
        """Upload a document from file content.
        Saves to S3 first, then creates the storage record.

        Args:
            user_id: ID of the user uploading the document
            document_name: Name of the document
            file_content: PDF file content as bytes

        Returns:
            Document ID

        Raises:
            DocumentAlreadyExistsError: If the document already exists
            S3UploadError: If S3 upload fails
            DatabaseWriteError: If database write fails
        """
        document_id, key = self.generate_document_id_key(user_id, content=file_content)

        # Check if document already exists before uploading
        if self.document_repository.document_exists(user_id, document_id):
            raise DocumentAlreadyExistsError(
                f"Document already exists with ID {document_id}",
                details={"document_id": document_id},
            )

        try:
            # 1. Upload to S3 first
            self.s3_client.upload_file(key, file_content)

            # 2. If S3 upload succeeds, create and save document record
            try:
                document = Document(
                    id=document_id,
                    user_id=user_id,
                    name=document_name,
                    source=DocumentSource.FILE,
                    source_url=None,
                    status=ProcessingStatus.PROCESSING,
                )
                self.document_repository.save_document(document)
                return document_id

            except DocumentAlreadyExistsError as db_exc:
                # Handle the case where the generated ID from content already exists
                raise db_exc
            except Exception as db_exc:
                raise DatabaseWriteError(
                    f"Database write failed after successful S3 upload for {key}",
                    details={"db_exc": str(db_exc)},
                )

        except Exception as s3_exc:
            raise S3UploadError(
                f"Failed to upload document to S3 ({key})",
                details={"s3_exc": str(s3_exc)},
            )

    def upload_from_url(self, user_id: str, document_name: str, url: str) -> str:
        """Upload a document from a URL.
        Downloads from URL, saves to S3 first, then creates the storage record.

        Args:
            user_id: ID of the user uploading the document
            document_name: Name of the document
            url: URL to download the PDF from

        Returns:
            Document ID

        Raises:
            DocumentAlreadyExistsError: If the document already exists
            URLDownloadError: If URL download fails
            S3UploadError: If S3 upload fails
            DatabaseWriteError: If database write fails
        """
        # First generate the ID from the URL before downloading content
        document_id, key = self.generate_document_id_key(user_id, url=url)

        # Check if document already exists before downloading and uploading
        if self.document_repository.document_exists(user_id, document_id):
            raise DocumentAlreadyExistsError(
                f"Document already exists with ID {document_id}",
                details={"document_id": document_id},
            )

        try:
            # 1. Download from URL
            response = requests.get(url)
            if response.status_code != 200:
                raise URLDownloadError(
                    f"Failed to download PDF from URL ({url}): {response.status_code}",
                    details={"status": str(response)},
                )
            content = response.content

            # 2. Upload downloaded content to S3
            self.s3_client.upload_file(key, content)

            # 3. If S3 upload succeeds, create and save storage record
            try:
                document = Document(
                    id=document_id,
                    user_id=user_id,
                    name=document_name,
                    source=DocumentSource.URL,
                    source_url=url,
                    status=ProcessingStatus.PROCESSING,
                )
                self.document_repository.save_document(document)
                return document_id

            except DocumentAlreadyExistsError as db_exc:
                raise db_exc
            except Exception as db_exc:
                raise DatabaseWriteError(
                    f"Database write failed after successful S3 upload for {key}",
                    details={"db_exc": str(db_exc)},
                )

        except Exception as upload_exc:
            raise S3UploadError(
                f"Failed to process document from URL ({url})",
                details={"upload_exc": str(upload_exc)},
            )
