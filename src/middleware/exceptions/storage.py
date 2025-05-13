"""Storage-related exceptions."""

from typing import Any, Dict, Optional

from . import PDFAnalysisError


class StorageError(PDFAnalysisError):
    """Base class for storage-related errors."""

    def __init__(
        self, message: str, code: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=500,  # Internal Server Error
        )

class StorageGeneralError(StorageError):
    """General error for storage operations."""

    def __init__(
        self,
        message: str = "Storage operation failed",
        code: str = "STORAGE_GENERAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)
        

class DocumentNotFoundError(StorageError):
    """Error when a document is not found in storage."""

    def __init__(
        self,
        document_id: str,
        message: str = "Document not found",
        code: str = "DOCUMENT_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            details={"document_id": document_id, **(details or {})},
        )


class PageNotFoundError(StorageError):
    """Error when a page is not found in storage."""

    def __init__(
        self,
        document_id: str,
        page_number: int,
        message: str = "Page not found",
        code: str = "PAGE_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            details={
                "document_id": document_id,
                "page_number": page_number,
                **(details or {}),
            },
        )


class StorageAccessError(StorageError):
    """Error when there are issues accessing storage (permissions, connectivity, etc.)."""

    def __init__(
        self,
        message: str = "Storage access error",
        code: str = "STORAGE_ACCESS_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class StorageValidationError(StorageError):
    """Error when stored data fails validation."""

    def __init__(
        self,
        message: str = "Storage validation error",
        code: str = "STORAGE_VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class DocumentAlreadyExistsError(StorageError):
    """Raised when attempting to create a document that already exists."""

    def __init__(
        self,
        message: str = "Document already exists",
        code: str = "DOCUMENT_ALREADY_EXISTS",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            details: Additional details about the error
        """
        super().__init__(message, code, details)


class StorageOperationError(StorageError):
    """Raised when a storage operation fails."""

    def __init__(self, message: str = "Storage operation failed", code: str = "STORAGE_OPERATION_FAILED",
        details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message
        """
        super().__init__(message, code, details)


class S3UploadError(StorageError):
    """Raised when an S3 upload operation fails."""

    def __init__(
        self,
        message: str = "Failed to upload document to S3",
        code: str = "S3_UPLOAD_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, details)


class URLDownloadError(StorageError):
    """Raised when a URL download operation fails."""

    def __init__(
        self,
        message: str = "Failed to download document from URL",
        code: str = "URL_DOWNLOAD_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, details)


class DatabaseWriteError(StorageError):
    """Raised when a database write operation fails."""

    def __init__(
        self,
        message: str = "Failed to write to the database",
        code: str = "DATABASE_WRITE_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, code, details)
