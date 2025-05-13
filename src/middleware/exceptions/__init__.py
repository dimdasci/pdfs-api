"""Exception handling for the PDF Analysis service."""

from typing import Any, Dict, Optional


class PDFAnalysisError(Exception):
    """Base exception for all PDF Analysis service errors."""

    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code


from .api import BadRequestError, ForbiddenError, NotFoundError, UnauthorizedError
from .business import (
    DocumentProcessingError,
    InvalidDocumentStateError,
    InvalidPageError,
    PDFValidationError,
)
from .storage import (
    DatabaseWriteError,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    PageNotFoundError,
    S3UploadError,
    StorageAccessError,
    StorageError,
    StorageGeneralError,
    StorageValidationError,
    URLDownloadError,
)

__all__ = [
    # Base
    "PDFAnalysisError",
    # API Errors
    "BadRequestError",
    "NotFoundError",
    "ForbiddenError",
    "UnauthorizedError",
    # Business Errors
    "DocumentProcessingError",
    "InvalidDocumentStateError",
    "InvalidPageError",
    "PDFValidationError",
    # Storage Errors
    "StorageError",
    "DocumentAlreadyExistsError",
    "DocumentNotFoundError",
    "PageNotFoundError",
    "StorageAccessError",
    "StorageValidationError",
    "StorageGeneralError",
    "S3UploadError",
    "URLDownloadError",
    "DatabaseWriteError",
]
