"""Module to process S3 events when PDF object is put."""

import subprocess
import tempfile
from pathlib import Path

from aws_lambda_powertools.utilities.data_classes import SQSEvent, event_source
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.clients.dynamodb import DynamoDBClient
from src.clients.s3 import S3Client
from src.config.app import AppConfig
from src.middleware.exceptions import DocumentNotFoundError, StorageError
from src.middleware.logging import logger, logging_middleware
from src.models.domain import ProcessingStatus
from src.pdf_processor import process_pdf
from src.repositories.dynamodb_document import DynamoDBDocumentRepository
from src.utils.sqs_event import parser

# --- Load Configuration and Initialize Services ---
try:
    app_config = AppConfig.from_env()
except Exception as e:
    logger.exception("CRITICAL: Failed to load configuration or initialize services.")
    # This error prevents the Lambda from functioning, raise to indicate failure
    raise RuntimeError(f"Initialization error: {e}") from e

# --- Initialize Global Clients ---
dynamodb_client = DynamoDBClient(app_config)
s3_client = S3Client(app_config)


@logging_middleware
@event_source(data_class=SQSEvent)
def lambda_handler(event: SQSEvent, context: LambdaContext) -> dict:
    """
    Lambda function handler to process S3 events.

    Args:
        event (dict): The event data from S3.
        context (LambdaContext): The context object provided by AWS Lambda.

    Returns:
        dict: A response indicating the result of the processing.
    """

    document_repository = DynamoDBDocumentRepository(dynamodb_client)

    for obj in parser(event):
        process_object(obj, document_repository, s3_client, context.aws_request_id)

    return {"statusCode": 200, "message": "Processing complete"}


def process_object(
    object: dict, repository: DynamoDBDocumentRepository, s3: S3Client, req_id: str
) -> None:
    """
    Process the S3 object.

    Args:
        object (dict): The S3 object to process.
        repository (DynamoDBDocumentRepository): The repository to use for processing.
        s3 (S3Client): The S3 client to use for processing.
        req_id (str): The request ID.
    """

    bucket = app_config.pdf_bucket_name

    # extract ids
    object_key = object["key"]
    # object_key has the format "<user_id>/<doc_id>/<file_name>"
    user_id, doc_id = object_key.split("/")[:2]

    # Log the bucket name and object key
    logger.debug(
        "Processing S3 event",
        extra={
            "object_key": object_key,
            "user_id": user_id,
            "doc_id": doc_id,
        },
    )

    # get document from repository using user_id and doc_id
    try:
        document = repository.get_document_by_id(user_id, doc_id)
    except DocumentNotFoundError:
        logger.error(
            "Document not found in DynamoDB",
            extra={
                "user_id": user_id,
                "doc_id": doc_id,
            },
        )
        return

    # create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_dir = Path(temp_dir) / req_id
        tmp_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Created temporary directory at {tmp_dir}")

        # download s3 object from bucket / object_key to tmp folder
        local_file_path = tmp_dir / "original.pdf"
        s3.download_file(
            bucket_name=bucket, object_key=object_key, file_path=str(local_file_path)
        )

        logger.debug(f"Downloaded S3 object {object_key} to {local_file_path}")

        # process pdf file
        document = process_pdf(
            working_dir=tmp_dir,
            document=document,
        )

        # update document in repository
        repository.update_document_fields(
            user_id=user_id,
            document_id=doc_id,
            updates={
                "page_count": document.page_count,
                "info": document.info,
                "status": ProcessingStatus.COMPLETED,
            },
        )

        logger.debug(f"Updated document {doc_id} with metadata")

        # sync all subdirectories and files in the tmp_dir to s3
        sync_pages_to_s3(
            s3=s3,
            pages_dir=tmp_dir / "pages",
            bucket=bucket,
            user_id=user_id,
            doc_id=doc_id,
        )

        # save all page bundles to repository in a single batch operation
        repository.save_pages(
            pages=document.pages,
            user_id=user_id,
            document_id=doc_id,
        )

        logger.debug(f"Saved {len(document.pages)} page bundles for document {doc_id}")

        logger.info(
            "PDF processing complete",
            extra={
                "user_id": user_id,
                "doc_id": doc_id,
                "page_count": document.page_count,
            },
        )


def sync_pages_to_s3(
    s3, pages_dir: Path, bucket: str, user_id: str, doc_id: str
) -> None:
    """
    Sync a directory with page renders to an S3 bucket.

    Args:
        s3 (S3Client): The S3 client to use for syncing.
        pages_dir (Path): The local directory to sync.
        bucket (str): The S3 bucket name.
        user_id (str): The user ID.
        doc_id (str): The document ID.
    """
    if pages_dir.exists():
        # Define the S3 prefix where to upload the processed files
        s3_prefix = f"{user_id}/{doc_id}/pages"

        try:
            # Sync pages directory to S3 using boto3
            logger.debug(f"Syncing {pages_dir} to s3://{bucket}/{s3_prefix}")
            s3.sync_directory(pages_dir, s3_prefix)
            logger.debug("S3 sync completed")
        except StorageError as e:
            logger.error(
                f"Failed to sync pages directory to S3: {str(e)}",
                extra={
                    "user_id": user_id,
                    "doc_id": doc_id,
                },
            )
    else:
        logger.warning(
            f"Pages directory not found at {pages_dir}",
            extra={
                "user_id": user_id,
                "doc_id": doc_id,
            },
        )
