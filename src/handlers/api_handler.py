import functools  # Import functools for partial
from datetime import datetime, timezone
from typing import List

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, CORSConfig
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.clients.dynamodb import DynamoDBClient
from src.clients.s3 import S3Client
from src.config.app import AppConfig
from src.handlers import handle_get_documents, handle_upload_document
from src.middleware.auth import create_inject_user_context_decorator
from src.middleware.error_handler import error_handler_middleware
from src.middleware.logging import logging_middleware
from src.models.api import (
    DocumentListItem,
    DocumentSummary,
    Layer,
    ObjectMeta,
    PageBundle,
    PageDetail,
    PageSize,
    VersionResponse,
)
from src.models.domain.enums import ProcessingStatus

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

# --- Load Configuration and Initialize Services ---
try:
    app_config = AppConfig.from_env()
    logger.info(
        "Configuration loaded successfully.",
        extra={
            "app_env": app_config.app_env,
            "version": app_config.version,
            "commit_hash": app_config.commit_hash,
        },
    )
except Exception as e:
    logger.exception("CRITICAL: Failed to load configuration or initialize services.")
    # This error prevents the Lambda from functioning, raise to indicate failure
    raise RuntimeError(f"Initialization error: {e}") from e

# --- Initialize Global Clients (or use DI pattern if preferred) ---
# Simple instantiation for now
dynamodb_client = DynamoDBClient(app_config)
s3_client = S3Client(app_config)

# --- Create User Context Decorator Instance ---
# Call the factory with the initialized app and logger
inject_user_context = create_inject_user_context_decorator(app, logger)


# --- API Route Handlers ---
@app.get("/version")
def get_version() -> VersionResponse:
    """Returns the application version."""
    display_version = f"{app_config.version}-B:{app_config.commit_hash[:7]}-{app_config.app_env[0].upper()}"
    logger.info(f"Version requested: {display_version}")
    return VersionResponse(version=display_version)


@app.get("/documents")
@inject_user_context
def get_documents() -> List[DocumentListItem]:
    """Handle GET /documents.

    Returns a list of all documents for the user.
    Requires authentication (handled by API Gateway Authorizer).
    User context is injected by @inject_user_context.
    """
    user_id = app.context.get("user_id", "unknown_context_fallback")
    logger.info("Executing get_documents", extra={"user_id": user_id})

    return handle_get_documents(
        app=app,  # Pass the app instance for context/event access
        dynamodb_client=dynamodb_client,
        logger=logger,
    )


@app.get("/documents/<docId>")
@inject_user_context
def get_document_summary(docId: str) -> DocumentSummary:
    """Handle GET /documents/{docId} (stub).

    Returns high-level metadata for a specific document.
    Requires authentication (handled by API Gateway Authorizer).
    User context is injected by @inject_user_context.
    """
    user_id = app.context.get("user_id", "unknown_context_fallback")
    logger.info(
        "Executing get_document_summary", extra={"user_id": user_id, "docId": docId}
    )

    # TODO: Implement actual data fetching for docId (checking ownership using user_id)
    logger.info(f"Received get document summary request for {docId} (stub)")
    if docId.startswith("nonexistent-doc") or not docId.endswith(
        user_id[:4]
    ):  # Simulate auth check
        # TODO: Raise a proper NotFoundError or ForbiddenError exception
        logger.warning(
            "Attempt to access non-existent or unauthorized doc",
            extra={"user_id": user_id, "docId": docId},
        )
        raise Exception("Document not found or access denied (stub exception)")

    return DocumentSummary(
        document_id=docId,
        status=ProcessingStatus.COMPLETED,
        pages=[
            PageDetail(page=1, width=612.0, height=792.0, layer_count=3),
            PageDetail(page=2, width=612.0, height=792.0, layer_count=2),
        ],
    )


@app.get("/documents/<docId>/pages/<page>")
@inject_user_context
def get_page_bundle(docId: str, page: str) -> PageBundle:
    """Handle GET /documents/{docId}/pages/{page} (stub).

    Fetches the Page Bundle (layer URLs, object metadata) for a page.
    Requires authentication (handled by API Gateway Authorizer).
    User context is injected by @inject_user_context.
    """
    user_id = app.context.get("user_id", "unknown_context_fallback")
    logger.info(
        "Executing get_page_bundle",
        extra={"user_id": user_id, "docId": docId, "page": page},
    )

    # TODO: Implement actual data fetching for docId and page (checking ownership using user_id)
    # TODO: Validate page number against document page count
    logger.info(f"Received get page bundle request for {docId}, page {page} (stub)")

    # Simulate auth check and existence
    if (
        docId.startswith("nonexistent-doc")
        or not docId.endswith(user_id[:4])
        or int(page) > 2
    ):
        # TODO: Raise a proper NotFoundError or ForbiddenError exception
        logger.warning(
            "Attempt to access non-existent or unauthorized page",
            extra={"user_id": user_id, "docId": docId, "page": page},
        )
        raise Exception("Page not found or access denied (stub exception)")

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


@app.post("/documents")
@inject_user_context
def post_documents_route():
    """Handle POST /documents request."""
    # Use functools.partial to pass dependencies to the actual handler
    bound_handler = functools.partial(
        handle_upload_document,
        app=app,  # Pass the app instance for context/event access
        app_config=app_config,
        dynamodb_client=dynamodb_client,
        s3_client=s3_client,
        logger=logger,
    )
    return bound_handler()


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
    # Logging of claims will now be handled within individual route handlers using app.current_event
    return app.resolve(event, context)
