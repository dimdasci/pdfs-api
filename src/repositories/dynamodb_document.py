"""DynamoDB implementation of document repository."""

from typing import Any, Dict, List, Optional

from ..clients.dynamodb import DynamoDBClient
from ..middleware.exceptions.storage import DocumentNotFoundError, StorageGeneralError
from ..models.domain.document import Document
from ..models.domain.page import Page
from ..models.storage.document_record import DocumentRecord
from ..models.storage.page_bundle_record import PageBundleRecord


class DynamoDBDocumentRepository:
    """DynamoDB implementation of document repository operations."""

    def __init__(self, dynamodb_client: DynamoDBClient) -> None:
        """Initialize the repository with a DynamoDB client.

        Args:
            dynamodb_client: Client for DynamoDB operations
        """
        self.dynamodb_client = dynamodb_client

    @staticmethod
    def document_pk(user_id: str) -> str:
        """Create a DynamoDB partition key for a user's documents.

        Args:
            user_id: The user ID

        Returns:
            Formatted partition key
        """
        return f"USER#{user_id}"

    @staticmethod
    def document_sk(document_id: str) -> str:
        """Create a DynamoDB sort key for a document.

        Args:
            document_id: The document ID

        Returns:
            Formatted sort key
        """
        return f"PDF#{document_id}"

    @staticmethod
    def page_bundle_sk(document_id: str, page_number: int) -> str:
        """Create a DynamoDB sort key for a page.

        Args:
            document_id: The document ID
            page_number: The page number

        Returns:
            Formatted sort key
        """
        return f"PDF#{document_id}#PAGE#{page_number:03d}"

    def save_document(self, document: Document) -> None:
        """Save a document to DynamoDB.

        Args:
            document: The Document domain object to save

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(document.user_id)
        sk = self.document_sk(document.id)
        record = DocumentRecord.from_domain(document).to_dict()
        self.dynamodb_client.put_item(
            {
                "PK": pk,
                "SK": sk,
                **record,
            }
        )

    def get_document_by_id(self, user_id: str, document_id: str) -> Document:
        """Retrieve a document from DynamoDB by user ID and document ID.

        Args:
            user_id: The user who owns the document
            document_id: The document identifier

        Returns:
            The Document domain object

        Raises:
            DocumentNotFoundError: If the document is not found
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        sk = self.document_sk(document_id)
        item = self.dynamodb_client.get_item(pk=pk, sk=sk)
        record = DocumentRecord.from_dict(item)
        return record.to_domain()

    def list_documents(
        self, user_id: str, status: Optional[str] = None, limit: int = 20
    ) -> List[Document]:
        """List documents for a user from DynamoDB, optionally filtered by status.

        Args:
            user_id: The user whose documents to list
            status: Optional status filter
            limit: Maximum number of documents to return

        Returns:
            List of Document domain objects

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        items = self.dynamodb_client.query_by_pk(pk=pk, limit=limit)
        docs = [DocumentRecord.from_dict(item).to_domain() for item in items]
        if status:
            docs = [d for d in docs if d.status == status]
        return docs

    def update_document_fields(
        self, user_id: str, document_id: str, updates: Dict[str, Any]
    ) -> None:
        """Update fields of a document in DynamoDB.

        Args:
            user_id: The user who owns the document
            document_id: The document identifier
            updates: Dictionary of fields to update

        Raises:
            DocumentNotFoundError: If the document is not found
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        sk = self.document_sk(document_id)
        self.dynamodb_client.update_item_fields(pk=pk, sk=sk, updates=updates)

    def save_page(self, page: Page, user_id: str, document_id: str) -> None:
        """Save a page to DynamoDB.

        Args:
            page: The Page to save
            user_id: The user who owns the document
            document_id: The document identifier

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        sk = self.page_bundle_sk(document_id, page.number)
        record = PageBundleRecord.from_domain(page, user_id, document_id).to_dict()
        page_bundle = {
            "PK": pk,
            "SK": sk,
            **record,
        }
        self.dynamodb_client.put_item(page_bundle)

    def get_page(self, user_id: str, document_id: str, page_number: int) -> Page:
        """Retrieve a page from DynamoDB.

        Args:
            user_id: The user who owns the document
            document_id: The document identifier
            page_number: The page number (1-based)

        Returns:
            The Page object

        Raises:
            DocumentNotFoundError: If the page is not found
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        sk = self.page_bundle_sk(document_id, page_number)
        item = self.dynamodb_client.get_item(pk=pk, sk=sk)
        return PageBundleRecord.from_dict(item).to_domain()

    def list_page_bundles(
        self, user_id: str, document_id: str
    ) -> List[PageBundleRecord]:
        """List all page bundle records for a document from DynamoDB.

        Args:
            user_id: The user who owns the document
            document_id: The document identifier

        Returns:
            List of PageBundleRecord objects

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        sk_prefix = f"PDF#{document_id}#PAGE#"
        items = self.dynamodb_client.query_by_pk_and_sk_prefix(
            pk=pk, sk_prefix=sk_prefix
        )
        return [PageBundleRecord.from_dict(item) for item in items]

    def list_pages(self, user_id: str, document_id: str) -> List[Page]:
        """List all pages for a document from DynamoDB.

        Args:
            user_id: The user who owns the document
            document_id: The document identifier

        Returns:
            List of Page objects

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        sk_prefix = f"PDF#{document_id}#PAGE#"
        items = self.dynamodb_client.query_by_pk_and_sk_prefix(
            pk=pk, sk_prefix=sk_prefix
        )
        return [PageBundleRecord.from_dict(item).to_domain() for item in items]

    def document_exists(self, user_id: str, document_id: str) -> bool:
        """Check if a document already exists.

        Args:
            user_id: The user who owns the document
            document_id: The document identifier

        Returns:
            True if document exists, False otherwise

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        sk = self.document_sk(document_id)
        try:
            item = self.dynamodb_client.get_item(pk=pk, sk=sk)
            return item is not None and len(item) > 0
        except DocumentNotFoundError:
            # Return False if the document is not found
            return False
        except Exception as e:
            raise StorageGeneralError(
                f"Failed to check document existence: {str(e)}",
                details={"pk": pk, "sk": sk},
            )
