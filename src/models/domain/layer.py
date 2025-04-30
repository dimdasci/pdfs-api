"""Layer domain model."""

from typing import List

from pydantic import BaseModel, Field

from .enums import PDFObjectType
from .pdf_object import PDFObject


class Layer(BaseModel):
    """A layer of PDF objects with the same z-index.

    Attributes:
        z_index: Z-index for rendering order
        type: Type of objects in this layer
        objects: List of PDF objects in this layer
    """

    z_index: int = Field(..., description="Z-index for rendering order")
    type: PDFObjectType = Field(..., description="Type of objects in this layer")
    objects: List[PDFObject] = Field(
        default_factory=list, description="List of PDF objects in this layer"
    )

    def add_object(self, obj: PDFObject) -> None:
        """Add a PDF object to the layer.

        Args:
            obj: PDF object to add

        Raises:
            ValueError: If object type doesn't match layer type
        """
        if obj.type != self.type:
            raise ValueError(
                f"Cannot add {obj.type} object to layer of type {self.type}"
            )
        self.objects.append(obj)

    @property
    def object_count(self) -> int:
        """Get number of objects in the layer."""
        return len(self.objects)
