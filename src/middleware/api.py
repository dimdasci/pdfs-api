"""Pydantic models for API Gateway events, responses, and data structures."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class APIErrorResponse(BaseModel):
    """Standardized error response for API endpoints.

    Attributes:
        message: Human-readable error message
        code: Error code string (e.g., from ErrorCode enum)
        details: Additional error context or details
    """

    message: str
    code: str
    details: Optional[Dict[str, Any]] = None


class VersionResponse(BaseModel):
    """Response containing the API version.

    Attributes:
        version: The version string
    """

    version: str


# --- Document Schemas (from api.yaml) ---


class UploadResponse(BaseModel):
    """Response for POST /documents.

    Matches UploadResponse schema in api.yaml.
    """

    document_id: str
    status: str  # processing, completed, failed


class DocumentListItem(BaseModel):
    """Item for GET /documents list response.

    Matches DocumentListItem schema in api.yaml.
    """

    document_id: str
    name: str
    status: str  # processing, completed, failed
    page_count: int
    uploaded: datetime


class PageDetail(BaseModel):
    """Nested page detail for DocumentSummary."""

    page: int = Field(..., ge=1)
    width: float
    height: float
    layer_count: int


class DocumentSummary(BaseModel):
    """Response for GET /documents/{docId}.

    Matches DocumentSummary schema in api.yaml.
    """

    document_id: str
    status: str  # processing, completed, failed
    pages: List[PageDetail]


# --- Page Bundle Schemas (from api.yaml) ---


class Layer(BaseModel):
    """Layer details within a PageBundle.

    Matches Layer schema in api.yaml.
    """

    z_index: int
    type: str  # text, path, image, shade, annot, form
    url: HttpUrl
    object_count: int


class ObjectMeta(BaseModel):
    """Object metadata within a PageBundle.

    Matches ObjectMeta schema in api.yaml.
    """

    id: str
    type: str  # text, path, image, shade, annot, form
    bbox: List[float] = Field(..., min_length=4, max_length=4)
    z_index: int


class PageSize(BaseModel):
    """Page dimensions."""

    width: float
    height: float


class PageBundle(BaseModel):
    """Response for GET /documents/{docId}/pages/{page}.

    Matches PageBundle schema in api.yaml.
    """

    document_id: str
    page: int = Field(..., ge=1)
    size: PageSize
    full_raster_url: HttpUrl
    layers: List[Layer]
    objects: List[ObjectMeta]
