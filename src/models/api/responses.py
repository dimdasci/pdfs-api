"""Response models for API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl

from src.models.domain.enums import ProcessingStatus


class APIErrorResponse(BaseModel):
    """Standardized error response for API endpoints.
    
    Attributes:
        message: Human-readable error message
        code: Error code string
        details: Additional error context or details
    """
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Error code string")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class VersionResponse(BaseModel):
    """Response for GET /version endpoint."""
    version: str = Field(..., description="API version string")


class UploadResponse(BaseModel):
    """Response for POST /documents endpoint."""
    document_id: str = Field(..., description="Unique document identifier")
    status: ProcessingStatus = Field(
        ...,
        description="Initial processing status"
    )


class DocumentListItem(BaseModel):
    """Item in the GET /documents list response."""
    document_id: str = Field(..., description="Unique document identifier")
    name: str = Field(..., description="Original filename")
    status: ProcessingStatus = Field(..., description="Current processing status")
    page_count: int = Field(..., ge=0, description="Total number of pages")
    uploaded: datetime = Field(..., description="Upload timestamp")


class PageDetail(BaseModel):
    """Page information in DocumentSummary."""
    page: int = Field(..., ge=1, description="Page number (1-based)")
    width: float = Field(..., gt=0, description="Page width in points")
    height: float = Field(..., gt=0, description="Page height in points")
    layer_count: int = Field(..., ge=0, description="Number of layers")


class DocumentSummary(BaseModel):
    """Response for GET /documents/{docId} endpoint."""
    document_id: str = Field(..., description="Unique document identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    pages: List[PageDetail] = Field(..., description="List of pages with basic info")


class Layer(BaseModel):
    """Layer information in PageBundle."""
    z_index: int = Field(..., description="Z-index for rendering order")
    type: str = Field(
        ...,
        pattern="^(text|path|image|shade|annot|form)$",
        description="Type of objects in this layer"
    )
    url: HttpUrl = Field(..., description="URL to layer's rendered image")
    object_count: int = Field(..., ge=0, description="Number of objects in layer")


class ObjectMeta(BaseModel):
    """Object metadata in PageBundle."""
    id: str = Field(..., description="Unique object identifier")
    type: str = Field(
        ...,
        pattern="^(text|path|image|shade|annot|form)$",
        description="Type of PDF object"
    )
    bbox: List[float] = Field(
        ...,
        min_items=4,
        max_items=4,
        description="Bounding box coordinates [x1, y1, x2, y2]"
    )
    z_index: int = Field(..., description="Z-index for rendering order")


class PageSize(BaseModel):
    """Page dimensions in PageBundle."""
    width: float = Field(..., gt=0, description="Page width in points")
    height: float = Field(..., gt=0, description="Page height in points")


class PageBundle(BaseModel):
    """Response for GET /documents/{docId}/pages/{page} endpoint."""
    document_id: str = Field(..., description="Document identifier")
    page: int = Field(..., ge=1, description="Page number (1-based)")
    size: PageSize = Field(..., description="Page dimensions")
    full_raster_url: HttpUrl = Field(..., description="URL to full page raster")
    layers: List[Layer] = Field(..., description="List of layer information")
    objects: List[ObjectMeta] = Field(..., description="List of object metadata") 