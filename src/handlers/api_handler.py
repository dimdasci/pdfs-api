import functools
from typing import List

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, CORSConfig
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.clients.dynamodb import DynamoDBClient
from src.clients.s3 import S3Client
from src.config.app import AppConfig
from src.handlers import (
    handle_get_document,
    handle_get_documents,
    handle_get_page_bundle,
    handle_upload_document,
)
from src.middleware.auth import create_inject_user_context_decorator
from src.middleware.error_handler import error_handler_middleware
from src.middleware.logging import logging_middleware
from src.models.api import (
    DocumentListItem,
    DocumentSummary,
    PageBundle,
    VersionResponse,
)

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
    logger.info("Executing get_documents")

    return handle_get_documents(
        app=app,  # Pass the app instance for context/event access
        dynamodb_client=dynamodb_client,
        logger=logger,
    )


@app.get("/documents/<docId>")
@inject_user_context
def get_document_summary(docId: str) -> DocumentSummary:
    """Handle GET /documents/{docId}.

    Returns metadata for a specific document.
    Requires authentication (handled by API Gateway Authorizer).
    User context is injected by @inject_user_context.
    """
    logger.info("Executing get_document_summary", extra={"docId": docId})

    return handle_get_document(
        app=app, dynamodb_client=dynamodb_client, logger=logger, document_id=docId
    )


@app.get("/documents/<docId>/pages/<page>")
@inject_user_context
def get_page_bundle(docId: str, page: str) -> PageBundle:
    """Handle GET /documents/{docId}/pages/{page}.

    Fetches the Page Bundle (layer URLs, object metadata) for a page.
    Requires authentication (handled by API Gateway Authorizer).
    User context is injected by @inject_user_context.
    """
    logger.info(
        "Executing get_page_bundle",
        extra={"docId": docId, "page": page},
    )

    try:
        page_number = int(page)
    except ValueError:
        raise ValueError(f"Invalid page number: {page}")

    return handle_get_page_bundle(
        app=app,
        dynamodb_client=dynamodb_client,
        s3_client=s3_client,
        logger=logger,
        document_id=docId,
        page_number=page_number,
    )


@app.post("/documents")
@inject_user_context
def post_documents_route():
    """Handle POST /documents request."""
    logger.info("Executing post_documents_route")

    return handle_upload_document(
        app=app,  # Pass the app instance for context/event access
        app_config=app_config,
        dynamodb_client=dynamodb_client,
        s3_client=s3_client,
        logger=logger,
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
    # Logging of claims will now be handled within individual route handlers using app.current_event
    return app.resolve(event, context)
