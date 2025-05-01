"""Repository for document data access operations."""

import uuid

from ..clients.storage_facade import StorageFacade
from ..models.domain.document import Document


class DocumentRepository:
    """Repository for document data access operations."""

    def __init__(
        self,
        storage_facade: StorageFacade,
    ) -> None:
        """Initialize document repository.

        Args:
            storage_facade: Facade for storage operations
        """
        self.storage_facade = storage_facade

    def generate_document_id(self) -> str:
        """Generate a unique document ID.

        This could potentially live elsewhere (e.g., a utility module or within the service layer that uses this repo),
        but is kept here for now based on the previous structure.
        """
        return f"doc_{uuid.uuid4().hex[:8]}"

    def save_document(self, document: Document) -> None:
        """Save a new document record using the storage facade."""
        self.storage_facade.save_document(document)

    def get_document_by_id(self, user_id: str, document_id: str) -> Document:
        """Get a document by user ID and document ID using the storage facade."""
        return self.storage_facade.get_document_by_id(user_id, document_id)
