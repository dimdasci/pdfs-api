"""Handler for get document by ID (GET /documents/{docId}).

This module provides functionality to retrieve document metadata
for a specific document ID.
"""

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import Logger

from ..clients.dynamodb import DynamoDBClient
from ..models.api import DocumentSummary
from ..repositories.dynamodb_document import DynamoDBDocumentRepository
from ..services.auth import AuthenticationService


def handle_get_document(
    app: APIGatewayHttpResolver,
    dynamodb_client: DynamoDBClient,
    logger: Logger,
    document_id: str,
) -> DocumentSummary:
    """Handle GET /documents/{docId} requests.

    Retrieves document metadata for the specified document ID.

    Args:
        app: The API Gateway resolver instance
        dynamodb_client: DynamoDB client for document metadata
        logger: Logger instance
        document_id: The document ID to retrieve

    Returns:
        DocumentSummary object with document metadata

    Raises:
        UnauthorizedError: If user authentication context is missing
        DocumentNotFoundError: If document doesn't exist or user doesn't have access
        StorageGeneralError: If storage operations fail
    """
    # Initialize services
    auth_service = AuthenticationService(app, logger)
    document_repository = DynamoDBDocumentRepository(dynamodb_client)

    # 1. Authentication check - will raise UnauthorizedError if missing
    user_id = auth_service.get_authenticated_user_id()

    # 2. Fetch document from repository - will raise DocumentNotFoundError if not found
    document = document_repository.get_document_by_id(user_id, document_id)

    # Debug the info field value
    logger.info(
        "Document retrieved",
        extra={
            "document_id": document.id,
            "user_id": document.user_id,
            "info_type": type(document.info).__name__
            if document.info is not None
            else "None",
            "info_present": document.info is not None,
        },
    )

    # 3. Convert to DocumentSummary for API response
    return DocumentSummary(
        document_id=document.id,
        name=document.name,
        status=document.status,
        size_in_bytes=document.size_in_bytes,
        page_count=document.page_count,
        source=document.source.value
        if hasattr(document.source, "value")
        else str(document.source),
        source_url=str(document.source_url) if document.source_url else None,
        uploaded=document.uploaded,
        info=document.info,
    )
