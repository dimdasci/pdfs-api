"""Request models for API endpoints."""

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# Custom file upload model to match what PowerTools parser returns for files
class FileContent(BaseModel):
    """Model for representing an uploaded file in multipart/form-data."""

    content: bytes = Field(..., description="The file content")
    content_type: str = Field(..., description="Content type of the file")
    file_name: str = Field(..., description="Original filename")


class UploadRequest(BaseModel):
    """Request model for POST /documents.

    Validates the multipart/form-data upload request.
    """

    file: bytes = Field(..., description="PDF file content")
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r".*\.pdf$",
        description="Original filename, must end with .pdf",
    )


class ListDocumentsRequest(BaseModel):
    """Query parameters for GET /documents.

    Handles filtering and pagination.
    """

    status: Optional[str] = Field(
        None,
        pattern="^(processing|completed|failed)$",
        description="Filter by processing status",
    )
    limit: Optional[int] = Field(
        20, ge=1, le=100, description="Maximum number of documents to return"
    )


class UploadResponse(BaseModel):
    """Response model for document upload.

    Attributes:
        document_id: Unique ID of the uploaded document.
        status: Current processing status of the document.
    """

    document_id: str = Field(..., description="Unique document identifier")
    status: str = Field(..., description="Processing status")


# Pydantic Model for Multipart Form Data used in upload handler
class UploadForm(BaseModel):
    """Model representing the expected fields in a multipart/form-data upload request."""

    documentName: str = Field(..., description="User-provided name for the document")
    file: Optional[FileContent] = Field(None, description="Optional PDF file upload")
    url: Optional[HttpUrl] = Field(None, description="Optional URL to fetch PDF from")
