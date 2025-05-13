"""Page bundle storage model."""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from ..domain.enums import PDFObjectType
from ..domain.page import Page
from ..domain.pdf_object import PDFObject  # Move import to top level


class LayerInfo(BaseModel):
    """Information about a layer in a page bundle.

    Attributes:
        z_index: Z-index for rendering order
        type: Type of objects in this layer
        object_count: Number of objects in this layer
    """

    z_index: int = Field(..., description="Z-index for rendering order")
    type: PDFObjectType = Field(..., description="Type of objects in this layer")
    object_count: int = Field(..., ge=0, description="Number of objects in this layer")


class ObjectInfo(BaseModel):
    """Information about a PDF object in a page bundle.

    Attributes:
        id: Unique object identifier
        type: Type of PDF object
        bbox: Bounding box coordinates [x1, y1, x2, y2]
        z_index: Z-index for rendering order
    """

    id: str = Field(..., description="Unique object identifier")
    type: PDFObjectType = Field(..., description="Type of PDF object")
    bbox: List[float] = Field(
        ...,
        min_items=4,
        max_items=4,
        description="Bounding box coordinates [x1, y1, x2, y2]",
    )
    z_index: int = Field(..., description="Z-index for rendering order")


class PageBundleRecord(BaseModel):
    """Storage record for a page bundle.

    Maps between domain Page model and storage format.

    Attributes:
        user_id: ID of the user who owns this document
        document_id: Unique document identifier
        page_number: Page number (1-based)
        width: Page width in points
        height: Page height in points
        full_raster_url: URL to the full page raster image
        layers: List of layer information
        objects: List of object information
        processed: Processing timestamp
    """

    user_id: str = Field(..., description="ID of the user who owns this document")
    document_id: str = Field(..., description="Unique document identifier")
    page_number: int = Field(..., gt=0, description="Page number (1-based)")
    width: float = Field(..., gt=0, description="Page width in points")
    height: float = Field(..., gt=0, description="Page height in points")
    full_raster_url: str = Field(..., description="URL to the full page raster image")
    layers: List[LayerInfo] = Field(..., description="List of layer information")
    objects: List[ObjectInfo] = Field(..., description="List of object information")
    processed: datetime = Field(..., description="Processing timestamp")

    @classmethod
    def from_domain(
        cls, page: Page, user_id: str, document_id: str
    ) -> "PageBundleRecord":
        """Create PageBundleRecord from domain Page.

        Args:
            page: Domain Page instance
            user_id: ID of the user who owns this document
            document_id: Unique document identifier

        Returns:
            PageBundleRecord instance
        """
        layers = [
            LayerInfo(
                z_index=layer.z_index, type=layer.type, object_count=layer.object_count
            )
            for layer in page.layers.values()
        ]

        objects = [
            ObjectInfo(id=obj.id, type=obj.type, bbox=obj.bbox, z_index=obj.z_index)
            for obj in page.objects
        ]

        return cls(
            user_id=user_id,
            document_id=document_id,
            page_number=page.number,
            width=page.width,
            height=page.height,
            full_raster_url=page.full_raster_url,
            layers=layers,
            objects=objects,
            processed=datetime.utcnow(),
        )

    def to_domain(self) -> Page:
        """Convert to domain Page.

        Returns:
            Domain Page instance
        """
        # Create base page
        page = Page(
            number=self.page_number,
            width=self.width,
            height=self.height,
        )

        # Add full_raster_url if it exists in the Page model
        if hasattr(Page, "full_raster_url"):
            setattr(page, "full_raster_url", self.full_raster_url)

        # Reconstruct all PDF objects
        for obj_info in self.objects:
            pdf_object = PDFObject(
                id=obj_info.id,
                type=obj_info.type,
                bbox=obj_info.bbox,
                z_index=obj_info.z_index,
            )
            page.add_object(pdf_object)

        return page

    def to_dict(self) -> Dict[str, Any]:
        """Convert to storage dictionary.

        Returns:
            Dictionary suitable for storage
        """
        return {
            "type": "PageBundle",
            "user_id": self.user_id,  # Add missing user_id field
            "document_id": self.document_id,
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "full_raster_url": self.full_raster_url,
            "layers": [layer.model_dump() for layer in self.layers],
            "objects": [obj.model_dump() for obj in self.objects],
            "created_at": self.processed.isoformat(),
        }

    @classmethod
    def from_dict(cls, item: Dict[str, Any]) -> "PageBundleRecord":
        """Create PageBundleRecord from dictionary item.

        Args:
            item: Storage dictionary representation

        Returns:
            PageBundleRecord instance
        """
        # Fix ISO date parsing by handling 'Z' timezone indicator
        created_at = item.get("created_at") or "2000-01-01T00:00:00"
        if created_at.endswith("Z"):
            created_at = created_at[:-1] + "+00:00"  # Replace Z with +00:00

        return cls(
            user_id=item.get("user_id"),
            document_id=item.get("document_id"),
            page_number=item.get("page_number"),
            width=item.get("width"),
            height=item.get("height"),
            full_raster_url=item.get("full_raster_url"),
            layers=[LayerInfo(**layer) for layer in item.get("layers", [])],
            objects=[ObjectInfo(**obj) for obj in item.get("objects", [])],
            processed=datetime.fromisoformat(created_at),
        )
