"""Page domain model."""

from typing import Dict, List

from pydantic import BaseModel, Field

from .enums import PDFObjectType
from .layer import Layer
from .pdf_object import PDFObject


class Page(BaseModel):
    """A single page from a PDF document.

    Attributes:
        number: Page number (1-based)
        width: Page width in points
        height: Page height in points
        layers: Dictionary of layers by z-index
        objects: List of PDF objects on this page
    """

    number: int = Field(..., gt=0, description="Page number (1-based)")
    width: float = Field(..., gt=0, description="Page width in points")
    height: float = Field(..., gt=0, description="Page height in points")
    layers: Dict[int, Layer] = Field(
        default_factory=dict, description="Dictionary of layers by z-index"
    )
    objects: List[PDFObject] = Field(
        default_factory=list, description="List of PDF objects on this page"
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

    def add_object(self, obj: PDFObject) -> None:
        """Add a PDF object to the page.

        Args:
            obj: PDF object to add
        """
        self.objects.append(obj)
        if obj.z_index not in self.layers:
            self.add_layer(Layer(z_index=obj.z_index, type=obj.type))
