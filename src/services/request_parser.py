"""Request parsing service for multipart form data."""

import base64
from typing import Any, Dict, Tuple

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import Logger

from ..middleware.exceptions import BadRequestError
from ..models.api.requests import UploadForm
from ..utils.multipart import DirectExtractor, MultipartParser, SimpleFormParser


class RequestParsingService:
    """Service for parsing HTTP request data."""

    def __init__(self, app: APIGatewayHttpResolver, logger: Logger):
        """Initialize request parsing service.

        Args:
            app: The API Gateway resolver instance
            logger: Logger instance
        """
        self.app = app
        self.logger = logger

    def get_multipart_content(self) -> Tuple[Any, str]:
        """Extract and prepare multipart request body and content type.

        Returns:
            Tuple of (body, content_type)

        Raises:
            BadRequestError: If content type is invalid or body can't be decoded
        """
        body = self.app.current_event.body
        headers = self.app.current_event.headers or {}
        content_type = headers.get("content-type", headers.get("Content-Type", ""))

        # Validate content type
        if not content_type or "multipart/form-data" not in content_type:
            raise BadRequestError(
                f"Content-Type must be multipart/form-data, got: {content_type}"
            )

        # Decode body if base64 encoded
        if self.app.current_event.is_base64_encoded:
            try:
                if isinstance(body, str):
                    body = base64.b64decode(body)
                else:
                    # If body is already a file-like object, read it, decode, and rewrap
                    body_content = body.read() if hasattr(body, "read") else body
                    body = base64.b64decode(body_content)

                self.logger.debug("Decoded base64 body for multipart parsing")
            except Exception as e:
                self.logger.error(f"Error decoding base64 body: {e}", exc_info=True)
                raise BadRequestError("Invalid base64 encoding in request body")

        return body, content_type

    def parse_upload_form(self, body: Any, content_type: str) -> UploadForm:
        """Parse multipart form data using multiple strategies.

        Args:
            body: The request body
            content_type: The Content-Type header

        Returns:
            Validated UploadForm instance

        Raises:
            BadRequestError: If all parsing strategies fail
        """
        form_data = None
        error_messages = []

        # Strategy 1: Main parser
        try:
            parser = MultipartParser(content_type, body)
            parsed_form = parser.parse()

            if parsed_form:
                self.logger.debug(
                    "Main parser succeeded",
                    extra={"parsed_form_keys": list(parsed_form.keys())},
                )
                form_data = UploadForm(**parsed_form)
        except Exception as e:
            error_messages.append(f"Main parser: {str(e)}")
            self.logger.warning(f"Main multipart parser failed: {e}", exc_info=True)

        # Strategy 2: Simple fallback parser
        if form_data is None:
            try:
                simple_parser = SimpleFormParser(content_type, body)
                fallback_form = simple_parser.parse()

                if fallback_form:
                    self.logger.debug(
                        "Fallback parser succeeded",
                        extra={"fallback_form_keys": list(fallback_form.keys())},
                    )
                    form_data = UploadForm(**fallback_form)
            except Exception as e:
                error_messages.append(f"Fallback parser: {str(e)}")
                self.logger.warning(f"Fallback parser failed: {e}", exc_info=True)

        # Strategy 3: Direct extraction
        if form_data is None:
            try:
                extractor = DirectExtractor(body)
                extracted_form = extractor.extract(["documentName", "url"])

                if extracted_form:
                    self.logger.debug(
                        "Direct extraction succeeded",
                        extra={"extracted_form": extracted_form},
                    )
                    form_data = UploadForm(**extracted_form)
            except Exception as e:
                error_messages.append(f"Direct extraction: {str(e)}")
                self.logger.warning(f"Direct extraction failed: {e}", exc_info=True)

        # If all strategies failed
        if form_data is None:
            error_detail = "; ".join(error_messages)
            self.logger.error(f"All parsing strategies failed: {error_detail}")
            raise BadRequestError(
                f"Failed to parse multipart form data: {error_detail}"
            )

        return form_data

    def validate_upload_form(self, form_data: UploadForm) -> None:
        """Validate upload form data.

        Args:
            form_data: Form data to validate

        Raises:
            BadRequestError: If validation fails
        """
        document_name = form_data.documentName
        file = form_data.file
        url = form_data.url

        # Validate input (either file or url, not both)
        if not file and not url:
            raise BadRequestError("Either 'file' or 'url' must be provided")
        if file and url:
            raise BadRequestError("Cannot provide both 'file' and 'url'")

        # Validate file type if present
        if file and file.content_type != "application/pdf":
            raise BadRequestError(
                f"Invalid file type: {file.content_type}. Only PDF is allowed."
            )
