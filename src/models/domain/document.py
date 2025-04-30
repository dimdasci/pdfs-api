"""Document domain model."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
from enum import Enum

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
        pages: Dictionary of pages by page number
    """
    id: str = Field(..., description="Unique document identifier")
    user_id: str = Field(..., description="ID of the user who owns this document")
    name: str = Field(..., description="User-provided name for the document")
    source: DocumentSource = Field(..., description="How the document was provided")
    source_url: Optional[HttpUrl] = Field(
        None,
        description="Original URL if document was fetched from URL"
    )
    status: ProcessingStatus = Field(
        default=ProcessingStatus.PROCESSING,
        description="Current processing status"
    )
    uploaded: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Upload timestamp"
    )
    pages: Dict[int, Page] = Field(
        default_factory=dict,
        description="Dictionary of pages by page number"
    )

    class Config:
        allow_mutation = True  # Allow state changes for domain logic

    @property
    def page_count(self) -> int:
        """Get total number of pages."""
        return len(self.pages)

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
            
        Raises:
            ValueError: If page number already exists
        """
        if page.number in self.pages:
            raise ValueError(f"Page {page.number} already exists")
        self.pages[page.number] = page

    def get_page(self, number: int) -> Optional[Page]:
        """Get page by number."""
        return self.pages.get(number)

    @property
    def is_processing_complete(self) -> bool:
        """Check if document processing is complete."""
        return self.status in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED)

    @property
    def dynamo_pk(self) -> str:
        """Get DynamoDB partition key."""
        return f"USER#{self.user_id}"

    @property
    def dynamo_sk(self) -> str:
        """Get DynamoDB sort key."""
        return f"PDF#{self.id}" 