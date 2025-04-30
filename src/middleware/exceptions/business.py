"""Business logic related exceptions."""

from typing import Any, Dict, Optional

from . import PDFAnalysisError


class BusinessError(PDFAnalysisError):
    """Base class for business logic errors."""
    
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
            status_code=422  # Unprocessable Entity
        )


class DocumentProcessingError(BusinessError):
    """Errors that occur during document processing."""
    
    def __init__(
        self,
        message: str = "Failed to process document",
        code: str = "PROCESSING_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, details)


class InvalidDocumentStateError(BusinessError):
    """Errors for invalid document state transitions."""
    
    def __init__(
        self,
        message: str = "Invalid document state",
        code: str = "INVALID_STATE",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, details)


class InvalidPageError(BusinessError):
    """Errors for invalid page operations."""
    
    def __init__(
        self,
        message: str = "Invalid page operation",
        code: str = "INVALID_PAGE",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, details)


class PDFValidationError(BusinessError):
    """Errors for PDF validation failures."""
    
    def __init__(
        self,
        message: str = "Invalid PDF file",
        code: str = "INVALID_PDF",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, details) 