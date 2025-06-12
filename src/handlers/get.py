"""Handler for get document by ID (GET /documents/{docId}).

This module provides functionality to retrieve document metadata
for a specific document ID.
"""

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import Logger
from pydantic import HttpUrl

from ..clients.dynamodb import DynamoDBClient
from ..clients.s3 import S3Client
from ..models.api import DocumentSummary, Layer, ObjectMeta, PageBundle, PageSize
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


def handle_get_page_bundle(
    app: APIGatewayHttpResolver,
    dynamodb_client: DynamoDBClient,
    s3_client: S3Client,
    logger: Logger,
    document_id: str,
    page_number: int,
) -> PageBundle:
    """Handle GET /documents/{docId}/pages/{page} requests.

    Retrieves page bundle data for the specified document and page.

    Args:
        app: The API Gateway resolver instance
        dynamodb_client: DynamoDB client for document metadata
        s3_client: S3 client for generating signed URLs
        logger: Logger instance
        document_id: The document ID to retrieve
        page_number: The page number to retrieve (1-based)

    Returns:
        PageBundle object with page metadata, layer information, and object metadata

    Raises:
        UnauthorizedError: If user authentication context is missing
        DocumentNotFoundError: If document or page doesn't exist or user doesn't have access
        StorageGeneralError: If storage operations fail
    """
    # Initialize services
    auth_service = AuthenticationService(app, logger)
    document_repository = DynamoDBDocumentRepository(dynamodb_client)

    # 1. Authentication check - will raise UnauthorizedError if missing
    user_id = auth_service.get_authenticated_user_id()

    # 2. Fetch page from repository - will raise DocumentNotFoundError if not found
    page = document_repository.get_page(user_id, document_id, page_number)

    # 3. Generate signed URLs for layer images
    page_path = f"{user_id}/{document_id}/pages/p{page_number:03d}"
    full_raster_url = s3_client.get_object_url(
        f"{page_path}/page.png",
        expires_in=3600,
    )

    # 4. Create layer information
    layers = []
    for z_index, layer in page.layers.items():
        layer_url = s3_client.get_object_url(
            f"{page_path}/l{z_index:03d}.png",
            expires_in=3600,
        )
        layers.append(
            Layer(
                z_index=z_index,
                type=layer.type.value,
                url=HttpUrl(layer_url),
                object_count=len(layer.objects),
                objects=[
                    ObjectMeta(
                        id=str(obj.id),
                        type=obj.type.value,
                        bbox=list(obj.bbox) if obj.bbox else [0, 0, 0, 0],
                        z_index=z_index,
                    )
                    for obj in layer.objects
                ],
            )
        )

    # 5. Create and return PageBundle response
    response = PageBundle(
        document_id=document_id,
        page=page_number,
        size=PageSize(width=page.width, height=page.height),
        full_raster_url=HttpUrl(full_raster_url),
        layers=sorted(layers, key=lambda x: x.z_index),
        zero_objects=[
            ObjectMeta(
                id=str(obj.id),
                type=obj.type.value,
                bbox=list(obj.bbox) if obj.bbox else [0, 0, 0, 0],
                z_index=0,  # Default z-index for zero area objects
            )
            for obj in page.zero_area_objects
        ],
    )

    return response
