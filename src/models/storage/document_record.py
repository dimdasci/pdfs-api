"""Document storage model for DynamoDB."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl

from ..domain.document import Document, DocumentSource
from ..domain.enums import ProcessingStatus


class DocumentRecord(BaseModel):
    """DynamoDB record for a PDF document.

    Maps between domain Document model and DynamoDB storage format.

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

    @property
    def pk(self) -> str:
        """Get partition key (user_id)."""
        return f"USER#{self.user_id}"

    @property
    def sk(self) -> str:
        """Get sort key (document_id)."""
        return f"PDF#{self.document_id}"

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
    def from_dynamo(cls, item: Dict[str, Any]) -> "DocumentRecord":
        """Create a DocumentRecord instance from a DynamoDB item dictionary.

        Handles potential minor discrepancies between DB item and model fields if needed.
        For now, it directly maps known fields.
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
                "uploaded"
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

    def to_dynamo(self) -> Dict[str, Any]:
        """Convert document record to DynamoDB item.

        Returns:
            Dictionary with DynamoDB structure
        """
        # Create base item with partition and sort keys
        item = {
            "PK": self.pk,
            "SK": self.sk,
            "Type": "Document",
            "DocumentId": self.document_id,
            "UserId": self.user_id,
            "Name": self.name,
            "Source": self.source.value
            if hasattr(self.source, "value")
            else str(self.source),
            "SourceUrl": str(self.source_url) if self.source_url else None,
            "Status": self.status.value
            if hasattr(self.status, "value")
            else str(self.status),
            "Uploaded": self.uploaded.isoformat() if self.uploaded else None,
        }

        # Add pages if any (as flattened attributes or nested map)
        if hasattr(self, "pages") and self.pages:
            # Simplified approach - store page count
            item["PageCount"] = len(self.pages)

            # For a full implementation, you would serialize pages in a way
            # that fits your access patterns (e.g., separate items or as JSON)

        return item
