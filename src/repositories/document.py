"""Repository for document data access operations."""

import uuid
from typing import Optional

from ..clients.dynamodb import DynamoDBClient
from ..models.domain.document import Document
from ..models.storage.document_record import DocumentRecord


class DocumentRepository:
    """Repository for document data access operations."""

    def __init__(
        self,
        dynamodb_client: DynamoDBClient,
    ) -> None:
        """Initialize document repository.

        Args:
            dynamodb_client: Client for DynamoDB operations
        """
        self.dynamodb_client = dynamodb_client

    def generate_document_id(self) -> str:
        """Generate a unique document ID.

        This could potentially live elsewhere (e.g., a utility module or within the service layer that uses this repo),
        but is kept here for now based on the previous structure.
        """
        return f"doc_{uuid.uuid4().hex[:8]}"

    async def save_document(self, document: Document) -> None:
        """Save a new document record to DynamoDB.

        Args:
            document: Document domain object to save

        Raises:
            DocumentAlreadyExistsError: If document already exists
            StorageError: If the save operation fails
        """
        # Convert to storage model
        record = DocumentRecord.from_domain(document)

        # Store in DynamoDB using the client
        await self.dynamodb_client.put_item(record.to_dynamo())

    async def get_document_by_id(
        self, user_id: str, document_id: str
    ) -> Optional[Document]:
        """Get a document by user ID and document ID.

        Args:
            user_id: ID of the user who owns the document
            document_id: ID of the document to get

        Returns:
            Document domain object if found, None otherwise

        Raises:
            StorageError: If the get operation fails
        """
        # Get from DynamoDB using the client
        item = await self.dynamodb_client.get_item(
            pk=f"USER#{user_id}", sk=f"PDF#{document_id}"
        )

        if not item:
            return None

        # Convert to domain model using the new classmethod
        record = DocumentRecord.from_dynamo(item)
        return record.to_domain()
