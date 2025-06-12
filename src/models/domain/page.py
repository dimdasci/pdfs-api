"""Page domain model."""

from typing import Optional

from pydantic import BaseModel, Field

from .layer import Layer
from .pdf_object import PDFObject

type Box = tuple[float, float, float, float]


class Page(BaseModel):
    """A single page from a PDF document.

    Attributes:
        number: Page number (1-based)
        width: Page width in points
        height: Page height in points
        layers: Dictionary of layers by z-index
    """

    number: int = Field(..., gt=0, description="Page number (1-based)")
    width: float = Field(..., gt=0, description="Page width in points")
    height: float = Field(..., gt=0, description="Page height in points")
    rotation: int = Field(0, description="Page rotation in degrees (0, 90, 180, 270)")
    mediabox: Optional[Box] = Field(None, description="Media box coordinates")
    cropbox: Optional[Box] = Field(None, description="Crop box coordinates")
    bleedbox: Optional[Box] = Field(None, description="Bleed box coordinates")
    trimbox: Optional[Box] = Field(None, description="Trim box coordinates")
    artbox: Optional[Box] = Field(None, description="Art box coordinates")
    bbox: Optional[Box] = Field(None, description="Bounding box coordinates")

    layers: dict[int, Layer] = Field(
        default_factory=dict, description="Dictionary of layers by z-index"
    )
    zero_area_objects: list[PDFObject] = Field(
        default_factory=list, description="List of zero area objects"
    )

    def add_layer(self, layer: Layer) -> None:
        """Add a layer to the page.

        Args:
            layer: Layer to add

        Raises:
            ValueError: If layer with same z-index exists
        """
        if layer.z_index in self.layers:
            raise ValueError(f"Layer with z-index {layer.z_index} already exists")
        self.layers[layer.z_index] = layer
