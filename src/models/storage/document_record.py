"""Document storage model."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl

from ..domain.document import Document, DocumentSource
from ..domain.enums import ProcessingStatus


class DocumentRecord(BaseModel):
    """Storage record for a PDF document.

    Maps between domain Document model and storage format.

    Attributes:
        user_id: ID of the user who owns this document
        document_id: Unique document identifier
        name: Original filename
        source: How the document was provided
        source_url: Original URL if document was fetched from URL
        status: Current processing status
        uploaded: Upload timestamp
        page_count: Number of pages in the document
    """

    user_id: str = Field(..., description="ID of the user who owns this document")
    document_id: str = Field(..., description="Unique document identifier")
    name: str = Field(..., description="Original filename")
    source: DocumentSource = Field(..., description="How the document was provided")
    source_url: Optional[HttpUrl] = Field(
        None, description="Original URL if document was fetched from URL"
    )
    status: ProcessingStatus = Field(..., description="Current processing status")
    uploaded: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Upload timestamp",
    )
    page_count: int = Field(0, ge=0, description="Number of pages in the document")

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentRecord":
        """Create DocumentRecord from domain Document.

        Args:
            document: Domain Document instance

        Returns:
            DocumentRecord instance
        """
        return cls(
            user_id=document.user_id,
            document_id=document.id,
            name=document.name,
            source=document.source,
            source_url=document.source_url,
            status=document.status,
            uploaded=document.uploaded,
            page_count=document.page_count,
        )

    @classmethod
    def from_dict(cls, item: Dict[str, Any]) -> "DocumentRecord":
        """Create a DocumentRecord instance from a dictionary.

        Handles potential minor discrepancies between storage item and model fields if needed.
        """
        # Basic mapping, can add more robust handling (e.g., type conversion if needed)
        return cls(
            user_id=item.get("user_id"),
            document_id=item.get("document_id"),
            name=item.get("name"),
            source=DocumentSource(item.get("source")),
            source_url=HttpUrl(item.get("source_url"))
            if item.get("source_url")
            else None,
            status=ProcessingStatus(
                item.get("status")
            ),  # Convert string status to enum
            uploaded=item.get(
                "created_at"
            ),  # Assumes stored as ISO string, Pydantic handles conversion
            page_count=item.get("page_count"),
        )

    def to_domain(self, pages: Optional[Dict] = None) -> Document:
        """Convert to domain Document.

        Args:
            pages: Optional dictionary of pages to include

        Returns:
            Domain Document instance
        """
        return Document(
            id=self.document_id,
            user_id=self.user_id,
            name=self.name,
            source=self.source,
            source_url=self.source_url,
            status=self.status,
            uploaded=self.uploaded,
            pages=pages or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert document record to storage dictionary.

        Returns:
            Dictionary suitable for storage
        """
        # Create base item with partition and sort keys
        item = {
            "type": "DOCUMENT",
            "user_id": self.user_id,
            "document_id": self.document_id,
            "name": self.name,
            "source": self.source.value
            if hasattr(self.source, "value")
            else str(self.source),
            "source_url": str(self.source_url) if self.source_url else None,
            "status": self.status.value
            if hasattr(self.status, "value")
            else str(self.status),
            "created_at": self.uploaded.isoformat() if self.uploaded else None,
        }

        # Add pages if any (as flattened attributes or nested map)
        if hasattr(self, "pages") and self.pages:
            # Simplified approach - store page count
            item["page_count"] = len(self.pages)

            # For a full implementation, you would serialize pages in a way
            # that fits your access patterns (e.g., separate items or as JSON)

        return item
