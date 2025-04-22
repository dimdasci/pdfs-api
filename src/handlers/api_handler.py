from datetime import datetime
from typing import List

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, CORSConfig
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.middleware.api import (
    DocumentListItem,
    DocumentSummary,
    Layer,
    ObjectMeta,
    PageBundle,
    PageDetail,
    PageSize,
    UploadResponse,
    VersionResponse,
)
from src.middleware.error_handler import error_handler_middleware

# Middleware
from src.middleware.logging import logging_middleware

# --- Constants and Setup ---
logger = Logger()

# Configure CORS
cors_config = CORSConfig(
    allow_origin="https://dimosaic.dev",
    allow_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize API Gateway resolver
app = APIGatewayHttpResolver(cors=cors_config)


# --- API Route Handlers ---


@app.get("/version")
def get_version() -> VersionResponse:
    """Returns the application version."""
    display_version = "0.0.1-alpha"
    logger.info(f"Version requested: {display_version}")
    return VersionResponse(version=display_version)


@app.post("/documents")
def upload_document() -> UploadResponse:
    """Handle POST /documents (stub).

    Accepts PDF upload and starts processing.
    Requires authentication.
    """
    # TODO: Implement actual upload logic (S3 presigned URL, etc.)
    # TODO: Implement authentication check
    logger.info("Received document upload request (stub)")
    return UploadResponse(document_id="new-doc-123", status="processing")


@app.get("/documents")
def get_documents() -> List[DocumentListItem]:
    """Handle GET /documents (stub).

    Returns a list of documents for the user.
    Requires authentication.
    Supports filtering and pagination (not implemented in stub).
    """
    # TODO: Implement actual data fetching from DB
    # TODO: Implement authentication check
    # TODO: Implement filtering (status) and pagination (limit)
    logger.info("Received get documents request (stub)")
    return [
        DocumentListItem(
            document_id="stub-doc-123",
            name="example.pdf",
            status="PROCESSING",
            page_count=10,
            uploaded=datetime.utcnow(),
        ),
        DocumentListItem(
            document_id="stub-doc-456",
            name="another.pdf",
            status="COMPLETE",
            page_count=5,
            uploaded=datetime.utcnow(),
        ),
    ]


@app.get("/documents/<docId>")
def get_document_summary(docId: str) -> DocumentSummary:
    """Handle GET /documents/{docId} (stub).

    Returns high-level metadata for a specific document.
    Requires authentication.
    """
    # TODO: Implement actual data fetching for docId
    # TODO: Implement authentication/authorization check for docId
    logger.info(f"Received get document summary request for {docId} (stub)")
    if docId == "nonexistent-doc":  # Simulate not found
        # TODO: Raise a proper NotFoundError exception
        raise Exception("Document not found (stub exception)")

    return DocumentSummary(
        document_id=docId,
        status="COMPLETED",
        pages=[
            PageDetail(page=1, width=612.0, height=792.0, layer_count=3),
            PageDetail(page=2, width=612.0, height=792.0, layer_count=2),
        ],
    )


@app.get("/documents/<docId>/pages/<page>")
def get_page_bundle(docId: str, page: str) -> PageBundle:
    """Handle GET /documents/{docId}/pages/{page} (stub).

    Fetches the Page Bundle (layer URLs, object metadata) for a page.
    Requires authentication.
    """
    # TODO: Implement actual data fetching for docId and page
    # TODO: Implement authentication/authorization check
    # TODO: Validate page number against document page count
    logger.info(f"Received get page bundle request for {docId}, page {page} (stub)")
    if docId == "nonexistent-doc" or int(page) > 2:  # Simulate not found
        # TODO: Raise a proper NotFoundError exception
        raise Exception("Page not found (stub exception)")

    # Generate dummy URLs safely using Pydantic's HttpUrl
    dummy_base_url = "https://dummy.storage.local/"

    return PageBundle(
        document_id=docId,
        page=page,
        size=PageSize(width=612.0, height=792.0),
        full_raster_url=f"{dummy_base_url}{docId}/page{page}/raster.png",
        layers=[
            Layer(
                z_index=0,
                type="text",
                url=f"{dummy_base_url}{docId}/page{page}/layer0.json",
                object_count=15,
            ),
            Layer(
                z_index=1,
                type="image",
                url=f"{dummy_base_url}{docId}/page{page}/layer1.json",
                object_count=2,
            ),
        ],
        objects=[
            ObjectMeta(
                id="obj1", type="text", bbox=[10.0, 10.0, 100.0, 50.0], z_index=0
            ),
            ObjectMeta(
                id="obj2", type="image", bbox=[150.0, 150.0, 300.0, 400.0], z_index=1
            ),
        ],
    )


# --- Main Lambda Entry Point ---
@error_handler_middleware
@logging_middleware
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Main Lambda handler function.

    Args:
        event: API Gateway proxy event
        context: Lambda context object

    Returns:
        API Gateway proxy response
    """
    return app.resolve(event, context)
