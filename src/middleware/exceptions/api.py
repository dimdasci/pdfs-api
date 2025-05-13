"""API-related exceptions."""

from typing import Any, Dict, Optional

from . import PDFAnalysisError


class APIError(PDFAnalysisError):
    """Base class for API-related errors."""

    pass


class BadRequestError(APIError):
    """400 Bad Request errors."""

    def __init__(
        self,
        message: str = "Invalid request",
        code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details, status_code=400)


class UnauthorizedError(APIError):
    """401 Unauthorized errors."""

    def __init__(
        self,
        message: str = "Authentication required",
        code: str = "UNAUTHORIZED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details, status_code=401)


class ForbiddenError(APIError):
    """403 Forbidden errors."""

    def __init__(
        self,
        message: str = "Access denied",
        code: str = "FORBIDDEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details, status_code=403)


class NotFoundError(APIError):
    """404 Not Found errors."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code=code, details=details, status_code=404)
