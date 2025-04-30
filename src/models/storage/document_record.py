"""Document storage model for DynamoDB."""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field

from ..domain.document import Document
from ..domain.enums import ProcessingStatus
from .base_record import BaseRecord


class DocumentRecord(BaseRecord):
    """DynamoDB record for a PDF document.
    
    Maps between domain Document model and DynamoDB storage format.
    
    Attributes:
        user_id: ID of the user who owns this document
        document_id: Unique document identifier
        name: Original filename
        status: Current processing status
        uploaded: Upload timestamp
        page_count: Number of pages in the document
    """
    user_id: str = Field(..., description="ID of the user who owns this document")
    document_id: str = Field(..., description="Unique document identifier")
    name: str = Field(..., description="Original filename")
    status: ProcessingStatus = Field(..., description="Current processing status")
    uploaded: datetime = Field(..., description="Upload timestamp")
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
            status=document.status,
            uploaded=document.uploaded,
            page_count=document.page_count
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
            status=self.status,
            uploaded=self.uploaded,
            pages=pages or {}
        ) 