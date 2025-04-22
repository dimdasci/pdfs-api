from enum import Enum
from http import HTTPStatus
from typing import Any, Dict, Optional

from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.middleware_factory import lambda_handler_decorator
from pydantic import BaseModel, ValidationError

from src.middleware.api import APIErrorResponse

logger = Logger()


class ErrorCode(Enum):
    VALIDATION_INVALID_INPUT = "VALIDATION_INVALID_INPUT"
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"

    @property
    def default_message(self) -> str:
        messages: Dict["ErrorCode", str] = {
            ErrorCode.VALIDATION_INVALID_INPUT: "Invalid input",
            ErrorCode.SYSTEM_INTERNAL_ERROR: "An unexpected error occurred",
        }
        return messages[self]

    @classmethod
    def from_exception(cls, e: Exception) -> "ErrorCode":
        """Map exceptions to error codes."""
        mappings: Dict[type, "ErrorCode"] = {
            ValidationError: ErrorCode.VALIDATION_INVALID_INPUT,
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


def create_error_response(
    status_code: HTTPStatus,
    error_response: ErrorResponse,
) -> Dict[str, Any]:
    """Helper to create standardized error responses with error codes."""
    # Convert ErrorResponse to APIErrorResponse
    api_error = APIErrorResponse(
        message=error_response.message,
        code=error_response.code,
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

    # --- Input Validation Errors ---
    except ValidationError as e:
        logger.warning(f"Input validation failed: {e}", exc_info=True)
        error_response = ErrorResponse.from_code(
            ErrorCode.VALIDATION_INVALID_INPUT, details={"errors": str(e)}
        )
        return create_error_response(HTTPStatus.BAD_REQUEST, error_response)

    # --- Generic Fallback Error ---
    except Exception as e:
        logger.exception("Unhandled internal server error")
        error_response = ErrorResponse.from_code(
            ErrorCode.SYSTEM_INTERNAL_ERROR, details={"error": str(e)}
        )
        return create_error_response(HTTPStatus.INTERNAL_SERVER_ERROR, error_response)
