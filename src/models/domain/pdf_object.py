"""PDF object domain model."""

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from .enums import PDFObjectType


class PDFObject(BaseModel):
    """A PDF object (text, path, image, etc.).

    Attributes:
        id: Unique object identifier
        type: Type of PDF object
        bbox: Bounding box coordinates [x1, y1, x2, y2]
        z_index: Z-index for rendering order
        content: Optional content (text, path data, etc.)
    """

    id: int = Field(..., description="Unique object identifier")
    type: PDFObjectType = Field(..., description="Type of PDF object")
    bbox: List[float] = Field(
        ...,
        min_items=4,
        max_items=4,
        description="Bounding box coordinates [x1, y1, x2, y2]",
    )
    z_index: Optional[int] = Field(None, description="Z-index for rendering order")
    content: Optional[str] = Field(
        None, description="Optional content (text, path data, etc.)"
    )

    @property
    def width(self) -> float:
        """Calculate width of the object."""
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        """Calculate height of the object."""
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> float:
        """Calculate area of the object."""
        return self.width * self.height

    @property
    def is_zero_area(self) -> bool:
        """Check if object has zero area."""
        return self.area <= 0.0001  # Small threshold for floating point comparison

    @property
    def position(self) -> Tuple[float, float]:
        """Get top-left position of the object."""
        return (self.bbox[0], self.bbox[1])
