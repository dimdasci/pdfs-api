"""Handler for document upload operations (POST /documents).

This module provides functionality to handle multipart/form-data uploads
for both direct file uploads and URL-based file retrievals.
"""

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import Logger

from ..clients.dynamodb import DynamoDBClient
from ..clients.s3 import S3Client
from ..config.app import AppConfig
from ..models.api import UploadResponse
from ..models.domain import ProcessingStatus
from ..repositories.dynamodb_document import DynamoDBDocumentRepository
from ..services.auth import AuthenticationService
from ..services.request_parser import RequestParsingService
from ..services.upload import UploadService


def handle_upload_document(
    app: APIGatewayHttpResolver,
    app_config: AppConfig,
    dynamodb_client: DynamoDBClient,
    s3_client: S3Client,
    logger: Logger,
) -> UploadResponse:
    """Handle POST /documents requests for PDF uploads.

    Parses multipart/form-data, validates input, and processes uploads
    from either direct file uploads or URL retrievals.

    Args:
        app: The API Gateway resolver instance
        app_config: Application configuration
        dynamodb_client: DynamoDB client for document metadata
        s3_client: S3 client for document storage
        logger: Logger instance

    Returns:
        UploadResponse with document ID and status

    Raises:
        BadRequestError: If request validation fails
        UnauthorizedError: If user authentication context is missing
        StorageGeneralError: If storage operations fail
        DocumentAlreadyExistsError: If document ID already exists
    """
    # Initialize services
    auth_service = AuthenticationService(app, logger)
    parser_service = RequestParsingService(app, logger)
    document_repository = DynamoDBDocumentRepository(dynamodb_client)
    upload_service = UploadService(app_config, document_repository, s3_client)

    # 1. Authentication check - will raise UnauthorizedError if missing
    user_id = auth_service.get_authenticated_user_id()

    # 2. Parse request content - will raise BadRequestError if invalid
    body, content_type = parser_service.get_multipart_content()
    form_data = parser_service.parse_upload_form(body, content_type)

    # 3. Validate form data - will raise BadRequestError if invalid
    parser_service.validate_upload_form(form_data)

    # 4. Process the upload based on type (file or URL)
    if form_data.file:
        logger.info(f"Uploading file '{form_data.file.file_name}' for user {user_id}")
        document_id = upload_service.upload_from_file(
            user_id=user_id,
            document_name=form_data.documentName,
            file_content=form_data.file.content,
        )
    else:
        logger.info(f"Uploading from URL for user {user_id}")
        document_id = upload_service.upload_from_url(
            user_id=user_id,
            document_name=form_data.documentName,
            url=str(form_data.url),
        )

    logger.info(f"Document {document_id} initiated with status PROCESSING")

    # 5. Return Pydantic model directly - resolver will handle serialization
    return UploadResponse(document_id=document_id, status=ProcessingStatus.PROCESSING)
