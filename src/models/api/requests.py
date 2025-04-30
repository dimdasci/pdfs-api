"""Request models for API endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class UploadRequest(BaseModel):
    """Request model for POST /documents.
    
    Validates the multipart/form-data upload request.
    """
    file: bytes = Field(
        ...,
        description="PDF file content"
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r".*\.pdf$",
        description="Original filename, must end with .pdf"
    )


class ListDocumentsRequest(BaseModel):
    """Query parameters for GET /documents.
    
    Handles filtering and pagination.
    """
    status: Optional[str] = Field(
        None,
        pattern="^(processing|completed|failed)$",
        description="Filter by processing status"
    )
    limit: Optional[int] = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of documents to return"
    ) 