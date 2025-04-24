import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Application configuration."""

    app_env: str = Field(
        description="Application environment (development or production)"
    )
    version: str = Field(description="Application version")
    commit_hash: str = Field(description="Commit hash")

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables.

        In 'dev' mode (default), it first loads variables from a .env file.
        In 'production' mode, it reads directly from environment variables.
        """

        app_env = os.getenv("APP_ENV", "local").lower()
        if app_env == "local":
            # For simplicity, assuming .env is in the current working directory or project root
            dotenv_path = Path(".env")  # Searches current dir and parent dirs
            load_dotenv(dotenv_path=dotenv_path, override=True)
        elif app_env not in ["dev", "prod"]:
            raise ValueError(f"Invalid app environment: {app_env}")

        version = os.getenv("VERSION", "unknown")
        commit_hash = os.getenv("COMMIT_HASH", "unknown")

        return cls(
            app_env=app_env,
            version=version,
            commit_hash=commit_hash,
        )
