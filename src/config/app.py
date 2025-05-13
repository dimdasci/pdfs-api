import os
from pathlib import Path

from aws_lambda_powertools.logging import Logger
from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = Logger()


class AppConfig(BaseModel):
    """Application configuration."""

    app_env: str = Field(
        description="Application environment (development or production)"
    )
    version: str = Field(description="Application version")
    commit_hash: str = Field(description="Commit hash")
    dynamodb_table_name: str = Field(
        default="dimosaic-app-prod", description="Name of the DynamoDB table"
    )
    pdf_bucket_name: str = Field(
        default="dimosaic-pdf-analyser-svhy308sv6",
        description="Name of the S3 bucket for PDF storage",
    )

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables.

        In 'dev' mode (default), it first loads variables from a .env file.
        In 'production' mode, it reads directly from environment variables.
        """

        app_env = os.getenv("APP_ENV", "local").lower()
        logger.debug("App environment", extra={"app_env": app_env})
        if app_env == "local":
            # For simplicity, assuming .env is in the current working directory or project root
            dotenv_path = Path(".env")  # Searches current dir and parent dirs
            load_dotenv(dotenv_path=dotenv_path, override=True)
            logger.debug("Loaded .env file", extra={"dotenv_path": dotenv_path})
        elif app_env not in ["dev", "prod"]:
            raise ValueError(f"Invalid app environment: {app_env}")

        version = os.getenv("VERSION", "unknown")
        commit_hash = os.getenv("COMMIT_HASH", "unknown")
        dynamodb_table_name = os.getenv("DYNAMODB_TABLE_NAME", "dimosaic-app-prod")
        pdf_bucket_name = os.getenv(
            "PDF_BUCKET_NAME", "dimosaic-pdf-analyser-svhy308sv6"
        )

        return cls(
            app_env=app_env,
            version=version,
            commit_hash=commit_hash,
            dynamodb_table_name=dynamodb_table_name,
            pdf_bucket_name=pdf_bucket_name,
        )
