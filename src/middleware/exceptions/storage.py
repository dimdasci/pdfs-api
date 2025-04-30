"""Storage-related exceptions."""

from typing import Any, Dict, Optional

from . import PDFAnalysisError


class StorageError(PDFAnalysisError):
    """Base class for storage-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            details=details,
            status_code=500  # Internal Server Error
        )


class DocumentNotFoundError(StorageError):
    """Error when a document is not found in storage."""
    
    def __init__(
        self,
        document_id: str,
        message: str = "Document not found",
        code: str = "DOCUMENT_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            details={
                "document_id": document_id,
                **(details or {})
            }
        )


class PageNotFoundError(StorageError):
    """Error when a page is not found in storage."""
    
    def __init__(
        self,
        document_id: str,
        page_number: int,
        message: str = "Page not found",
        code: str = "PAGE_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            details={
                "document_id": document_id,
                "page_number": page_number,
                **(details or {})
            }
        )


class StorageAccessError(StorageError):
    """Error when there are issues accessing storage (permissions, connectivity, etc.)."""
    
    def __init__(
        self,
        message: str = "Storage access error",
        code: str = "STORAGE_ACCESS_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, details)


class StorageValidationError(StorageError):
    """Error when stored data fails validation."""
    
    def __init__(
        self,
        message: str = "Storage validation error",
        code: str = "STORAGE_VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, details) 