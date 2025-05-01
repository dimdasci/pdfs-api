from typing import Any, Dict, List, Optional, Protocol

from ..models.domain.document import Document
from ..models.storage.document_record import DocumentRecord
from ..models.storage.page_bundle_record import PageBundleRecord
from .dynamodb import DynamoDBClient


class StorageFacade(Protocol):
    def save_document(self, document: Document) -> None:
        """Save a new document record to storage.

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
        """Update fields of a document record.

        Args:
            user_id: The user who owns the document.
            document_id: The document identifier.
            updates: Dictionary of fields to update.
        Raises:
            DocumentNotFoundError: If the document is not found.
            StorageError: If the update operation fails.
        """
        ...

    def save_page_bundle(self, page_bundle: PageBundleRecord) -> None:
        """Save a new page bundle record to storage.

        Args:
            page_bundle: The PageBundleRecord to save.
        Raises:
            StorageError: If the save operation fails.
        """
        ...

    def get_page_bundle(
        self, user_id: str, document_id: str, page_number: int
    ) -> PageBundleRecord:
        """Retrieve a page bundle by user, document, and page number.

        Args:
            user_id: The user who owns the document.
            document_id: The document identifier.
            page_number: The page number (1-based).
        Returns:
            The PageBundleRecord.
        Raises:
            DocumentNotFoundError: If the page bundle is not found.
            StorageError: If the retrieval fails.
        """
        ...

    def list_page_bundles(
        self, user_id: str, document_id: str
    ) -> List[PageBundleRecord]:
        """List all page bundles for a document.

        Args:
            user_id: The user who owns the document.
            document_id: The document identifier.
        Returns:
            List of PageBundleRecord objects.
        Raises:
            StorageError: If the list operation fails.
        """
        ...


class DynamoDBStorageFacade(StorageFacade):
    def __init__(self, dynamodb_client: DynamoDBClient):
        self.dynamodb_client = dynamodb_client

    @staticmethod
    def document_pk(user_id: str) -> str:
        return f"USER#{user_id}"

    @staticmethod
    def document_sk(document_id: str) -> str:
        return f"PDF#{document_id}"

    @staticmethod
    def page_bundle_sk(document_id: str, page_number: int) -> str:
        return f"PDF#{document_id}#PAGE#{page_number:03d}"

    def save_document(self, document: Document) -> None:
        record = DocumentRecord.from_domain(document)
        self.dynamodb_client.put_item(record.to_dynamo())

    def get_document_by_id(self, user_id: str, document_id: str) -> Document:
        pk = self.document_pk(user_id)
        sk = self.document_sk(document_id)
        item = self.dynamodb_client.get_item(pk=pk, sk=sk)
        record = DocumentRecord.from_dynamo(item)
        return record.to_domain()

    def list_documents(
        self, user_id: str, status: Optional[str] = None, limit: int = 20
    ) -> List[Document]:
        pk = self.document_pk(user_id)
        items = self.dynamodb_client.query_by_pk(pk=pk, limit=limit)
        docs = [DocumentRecord.from_dynamo(item).to_domain() for item in items]
        if status:
            docs = [d for d in docs if d.status == status]
        return docs

    def update_document_fields(
        self, user_id: str, document_id: str, updates: Dict[str, Any]
    ) -> None:
        pk = self.document_pk(user_id)
        sk = self.document_sk(document_id)
        self.dynamodb_client.update_item_fields(pk=pk, sk=sk, updates=updates)

    def save_page_bundle(self, page_bundle: PageBundleRecord) -> None:
        self.dynamodb_client.put_item(page_bundle.to_dynamo())

    def get_page_bundle(
        self, user_id: str, document_id: str, page_number: int
    ) -> PageBundleRecord:
        pk = self.document_pk(user_id)
        sk = self.page_bundle_sk(document_id, page_number)
        item = self.dynamodb_client.get_item(pk=pk, sk=sk)
        return PageBundleRecord.from_dynamo(item)

    def list_page_bundles(
        self, user_id: str, document_id: str
    ) -> List[PageBundleRecord]:
        pk = self.document_pk(user_id)
        sk_prefix = f"PDF#{document_id}#PAGE#"
        items = self.dynamodb_client.query_by_pk_and_sk_prefix(
            pk=pk, sk_prefix=sk_prefix
        )
        return [PageBundleRecord.from_dynamo(item) for item in items]
