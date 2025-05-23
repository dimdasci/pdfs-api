"""Document domain model."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl

from .enums import ProcessingStatus
from .page import Page


class DocumentSource(str, Enum):
    """Source of the document."""

    FILE = "file"
    URL = "url"


class Document(BaseModel):
    """A PDF document being analyzed.

    This is the aggregate root for the PDF analysis domain.

    Attributes:
        id: Unique document identifier
        user_id: ID of the user who owns this document
        name: User-provided name for the document
        source: How the document was provided (file upload or URL)
        source_url: Original URL if document was fetched from URL
        status: Current processing status
        uploaded: Upload timestamp
        size_in_bytes: Size of the document in bytes
        page_count: Total number of pages
        info: Dictionary of document meta-data
        pages: Dictionary of pages by page number
    """

    id: str = Field(..., description="Unique document identifier")
    user_id: str = Field(..., description="ID of the user who owns this document")
    name: str = Field(..., description="User-provided name for the document")
    source: DocumentSource = Field(..., description="How the document was provided")
    source_url: Optional[HttpUrl] = Field(
        None, description="Original URL if document was fetched from URL"
    )
    status: ProcessingStatus = Field(
        default=ProcessingStatus.PROCESSING, description="Current processing status"
    )
    uploaded: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Upload timestamp",
    )
    size_in_bytes: int = Field(default=0, description="Size of the document in bytes")
    page_count: Optional[int] = Field(
        default=None,
        description="Total number of pages in the document after processing",
    )
    info: Optional[Dict[str, Union[str, int]]] = Field(
        default=None, description="Dictionary of document meta-data"
    )
    pages: List[Page] = Field(default_factory=list, description="List of pages")

    def update_status(self, new_status: ProcessingStatus) -> None:
        """Update document status if transition is valid.

        Args:
            new_status: New status to transition to

        Raises:
            ValueError: If status transition is invalid
        """
        if not self.status.can_transition_to(new_status):
            raise ValueError(
                f"Invalid status transition from {self.status} to {new_status}"
            )
        self.status = new_status

    def add_page(self, page: Page) -> None:
        """Add a page to the document.

        Args:
            page: Page to add
        """
        self.pages.append(page)
        self.page_count = len(self.pages)

    def get_page(self, number: int) -> Optional[Page]:
        """Get page by number."""
        return self.pages[number] if number in self.pages else None
