from enum import Enum
from http import HTTPStatus
from typing import Any, Dict, Optional

from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.middleware_factory import lambda_handler_decorator
from pydantic import BaseModel, ValidationError

from .api import APIErrorResponse
from .exceptions import (
    BadRequestError,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    ForbiddenError,
    NotFoundError,
    PDFAnalysisError,
    PDFValidationError,
    StorageError,
    UnauthorizedError,
)

logger = Logger()


class ErrorCode(Enum):
    # Validation errors
    VALIDATION_INVALID_INPUT = "VALIDATION_INVALID_INPUT"

    # API errors
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"

    # Business errors
    INVALID_PDF = "INVALID_PDF"

    # Storage errors
    STORAGE_ERROR = "STORAGE_ERROR"
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    DOCUMENT_ALREADY_EXISTS = "DOCUMENT_ALREADY_EXISTS"

    # System errors
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"

    @property
    def default_message(self) -> str:
        messages: Dict["ErrorCode", str] = {
            ErrorCode.VALIDATION_INVALID_INPUT: "Invalid input",
            ErrorCode.BAD_REQUEST: "Bad request",
            ErrorCode.UNAUTHORIZED: "Authentication required",
            ErrorCode.FORBIDDEN: "Access denied",
            ErrorCode.NOT_FOUND: "Resource not found",
            ErrorCode.INVALID_PDF: "Invalid PDF file",
            ErrorCode.STORAGE_ERROR: "Storage operation failed",
            ErrorCode.DOCUMENT_NOT_FOUND: "Document not found",
            ErrorCode.DOCUMENT_ALREADY_EXISTS: "Document already exists",
            ErrorCode.SYSTEM_INTERNAL_ERROR: "An unexpected error occurred",
        }
        return messages[self]

    @classmethod
    def from_exception(cls, e: Exception) -> "ErrorCode":
        """Map exceptions to error codes."""
        mappings: Dict[type, "ErrorCode"] = {
            ValidationError: ErrorCode.VALIDATION_INVALID_INPUT,
            BadRequestError: ErrorCode.BAD_REQUEST,
            UnauthorizedError: ErrorCode.UNAUTHORIZED,
            ForbiddenError: ErrorCode.FORBIDDEN,
            NotFoundError: ErrorCode.NOT_FOUND,
            DocumentNotFoundError: ErrorCode.DOCUMENT_NOT_FOUND,
            DocumentAlreadyExistsError: ErrorCode.DOCUMENT_ALREADY_EXISTS,
            PDFValidationError: ErrorCode.INVALID_PDF,
            StorageError: ErrorCode.STORAGE_ERROR,
        }
        return mappings.get(type(e), ErrorCode.SYSTEM_INTERNAL_ERROR)


class ErrorResponse(BaseModel):
    message: str
    code: ErrorCode
    details: Optional[Dict[str, Any]] = None

    @classmethod
    def from_code(
        cls, code: ErrorCode, details: Optional[Dict[str, Any]] = None
    ) -> "ErrorResponse":
        return cls(message=code.default_message, code=code, details=details)

    @classmethod
    def from_exception(cls, e: Exception) -> "ErrorResponse":
        """Create an ErrorResponse from an exception."""
        code = ErrorCode.from_exception(e)
        message = str(e) if str(e) else code.default_message
        details = getattr(e, "details", None)

        return cls(message=message, code=code, details=details)


def create_error_response(
    status_code: HTTPStatus,
    error_response: ErrorResponse,
) -> Dict[str, Any]:
    """Helper to create standardized error responses with error codes."""
    # Convert ErrorResponse to APIErrorResponse
    api_error = APIErrorResponse(
        message=error_response.message,
        code=error_response.code.value,  # Use the string value of the enum
        details=error_response.details,
    )

    return {
        "statusCode": status_code,
        "body": api_error.model_dump_json(),
        "headers": {"Content-Type": "application/json"},
    }


@lambda_handler_decorator
def error_handler_middleware(handler, event, context):
    """Middleware to handle exceptions and format error responses with error codes."""
    try:
        return handler(event, context)

    # --- PDFAnalysisError exceptions (our custom exceptions) ---
    except PDFAnalysisError as e:
        log_level = "warning" if e.status_code < 500 else "error"
        getattr(logger, log_level)(
            f"{e.__class__.__name__}: {str(e)}",
            extra={"code": e.code, "details": e.details},
        )

        error_response = ErrorResponse.from_exception(e)
        return create_error_response(HTTPStatus(e.status_code), error_response)

    # --- Input Validation Errors ---
    except ValidationError as e:
        logger.warning(f"Input validation failed: {e}", exc_info=True)
        error_response = ErrorResponse.from_code(
            ErrorCode.VALIDATION_INVALID_INPUT, details={"errors": str(e)}
        )
        return create_error_response(HTTPStatus.BAD_REQUEST, error_response)

    # --- Generic Fallback Error ---
    except Exception as e:
        logger.exception(f"Unhandled error: {e.__class__.__name__}: {str(e)}")
        error_response = ErrorResponse.from_code(
            ErrorCode.SYSTEM_INTERNAL_ERROR, details={"error": str(e)}
        )
        return create_error_response(HTTPStatus.INTERNAL_SERVER_ERROR, error_response)
