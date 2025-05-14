"""Handler for get list of documents (GET /documents).

This module provides functionality to retrieve a list of documents
for a user.
"""

from typing import List

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import Logger

from ..clients.dynamodb import DynamoDBClient
from ..models.api import DocumentListItem
from ..models.domain import Document
from ..repositories.dynamodb_document import DynamoDBDocumentRepository
from ..services.auth import AuthenticationService


def handle_get_documents(
    app: APIGatewayHttpResolver,
    dynamodb_client: DynamoDBClient,
    logger: Logger,
) -> List[DocumentListItem]:
    """Handle GET /documents requests.

    Retrieves a list of documents for the authenticated user.

    Args:
        app: The API Gateway resolver instance
        dynamodb_client: DynamoDB client for document metadata
        logger: Logger instance

    Returns:
        List of DocumentListItem objects

    Raises:
        UnauthorizedError: If user authentication context is missing
        StorageGeneralError: If storage operations fail
    """
    # Initialize services
    auth_service = AuthenticationService(app, logger)
    document_repository = DynamoDBDocumentRepository(dynamodb_client)

    # 1. Authentication check - will raise UnauthorizedError if missing
    user_id = auth_service.get_authenticated_user_id()

    # 2. Fetch documents from repository - will raise StorageGeneralError if fails
    documents: List[Document] = document_repository.list_documents(user_id)

    # Convert to List[DocumentListItem] for API response
    document_items: List[DocumentListItem] = [
        DocumentListItem(
            document_id=doc.id,
            name=doc.name,
            status=doc.status,
            page_count=doc.page_count,
            size_in_bytes=doc.size_in_bytes,
            uploaded=doc.uploaded,
        )
        for doc in documents
    ]

    return document_items
