"""Repository interfaces for document data access operations."""

import uuid
from typing import Any, Dict, List, Optional, Protocol

from ..models.domain.document import Document
from ..models.domain.page import Page
from ..models.storage.page_bundle_record import PageBundleRecord


class DocumentRepository(Protocol):
    """Interface for document repository operations."""

    def save_document(self, document: Document) -> None:
        """Save a document to storage.

        Args:
            document: The Document domain object to save.
        Raises:
            DocumentAlreadyExistsError: If the document already exists.
            StorageError: If the save operation fails.
        """
        ...

    def get_document_by_id(self, user_id: str, document_id: str) -> Document:
        """Retrieve a document by user ID and document ID.

        Args:
            user_id: The user who owns the document.
            document_id: The document identifier.
        Returns:
            The Document domain object.
        Raises:
            DocumentNotFoundError: If the document is not found.
            StorageError: If the retrieval fails.
        """
        ...

    def list_documents(
        self, user_id: str, status: Optional[str] = None, limit: int = 20
    ) -> List[Document]:
        """List documents for a user, optionally filtered by status.

        Args:
            user_id: The user whose documents to list.
            status: Optional status filter (processing, completed, failed).
            limit: Maximum number of documents to return.
        Returns:
            List of Document domain objects.
        Raises:
            StorageError: If the list operation fails.
        """
        ...

    def update_document_fields(
        self, user_id: str, document_id: str, updates: Dict[str, Any]
    ) -> None:
        """Update fields of a document.

        Args:
            user_id: The user who owns the document.
            document_id: The document identifier.
            updates: Dictionary of fields to update.
        Raises:
            DocumentNotFoundError: If the document is not found.
            StorageError: If the update operation fails.
        """
        ...

    def save_page(self, page: Page, user_id: str, document_id: str) -> None:
        """Save a page to storage.

        Args:
            page: The Page to save.
            user_id: The user who owns the document.
            document_id: The document identifier.
        Raises:
            StorageError: If the save operation fails.
        """
        ...

    def get_page(self, user_id: str, document_id: str, page_number: int) -> Page:
        """Retrieve a page by user, document, and page number.

        Args:
            user_id: The user who owns the document.
            document_id: The document identifier.
            page_number: The page number (1-based).
        Returns:
            The Page object.
        Raises:
            DocumentNotFoundError: If the page is not found.
            StorageError: If the retrieval fails.
        """
        ...

    def list_page_bundles(
        self, user_id: str, document_id: str
    ) -> List[PageBundleRecord]:
        """List all page bundle records for a document.

        Args:
            user_id: The user who owns the document.
            document_id: The document identifier.
        Returns:
            List of PageBundleRecord objects.
        Raises:
            StorageError: If the list operation fails.
        """
        ...

    def list_pages(self, user_id: str, document_id: str) -> List[Page]:
        """List all pages for a document.

        Args:
            user_id: The user who owns the document.
            document_id: The document identifier.
        Returns:
            List of Page objects.
        Raises:
            StorageError: If the list operation fails.
        """
        ...


def generate_document_id() -> str:
    """Generate a unique document ID.

    Returns:
        A unique document ID string
    """
    return f"doc_{uuid.uuid4().hex[:8]}"
