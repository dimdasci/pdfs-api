"""Unit tests for the DynamoDB Document Repository."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.clients.dynamodb import DynamoDBClient
from src.middleware.exceptions.storage import StorageError
from src.models.domain.document import Document, DocumentSource
from src.models.domain.enums import ProcessingStatus
from src.repositories.dynamodb_document import DynamoDBDocumentRepository


class TestDynamoDBDocumentRepository(unittest.TestCase):
    """Test cases for the DynamoDB Document Repository."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_dynamodb_client = MagicMock(spec=DynamoDBClient)
        self.repo = DynamoDBDocumentRepository(self.mock_dynamodb_client)

    def test_list_documents_success(self):
        """Test successful retrieval of documents."""
        # Arrange
        user_id = "test-user-123"
        now = datetime.now()

        # Create mock DynamoDB items that would be returned by the query.
        # Note: Only items with SK prefix "PDF#" should be returned by the query.
        mock_items = [
            {
                "PK": f"USER#{user_id}",
                "SK": "PDF#doc1",
                "document_id": "doc1",
                "name": "Test Document 1",
                "type": "DOCUMENT",  # Add type field
                "status": "completed",
                "page_count": 5,  # Add page_count for the completed document
                "user_id": user_id,
                "size_in_bytes": 1024,
                "created_at": now.isoformat(),
                "source": "file",
            },
            {
                "PK": f"USER#{user_id}",
                "SK": "PDF#doc2",
                "document_id": "doc2",
                "name": "Test Document 2",
                "type": "DOCUMENT",  # Add type field
                "status": "processing",
                "page_count": 0,  # Processing document has no pages yet
                "user_id": user_id,
                "size_in_bytes": 2048,
                "created_at": now.isoformat(),
                "source": "url",
            },
        ]

        # Configure the mock to return our test items
        self.mock_dynamodb_client.query_by_pk_and_sk_prefix.return_value = mock_items

        # Act
        documents = self.repo.list_documents(user_id)

        # Assert
        self.assertEqual(2, len(documents))
        self.mock_dynamodb_client.query_by_pk_and_sk_prefix.assert_called_once_with(
            pk=f"USER#{user_id}", sk_prefix="PDF#"
        )

        # Verify first document (completed)
        self.assertEqual("doc1", documents[0].id)
        self.assertEqual("Test Document 1", documents[0].name)
        self.assertEqual(ProcessingStatus.COMPLETED, documents[0].status)
        self.assertEqual(5, documents[0].page_count)  # Should have 5 pages
        self.assertEqual(1024, documents[0].size_in_bytes)

        # Verify second document (processing)
        self.assertEqual("doc2", documents[1].id)
        self.assertEqual("Test Document 2", documents[1].name)
        self.assertEqual(ProcessingStatus.PROCESSING, documents[1].status)
        self.assertEqual(
            0, documents[1].page_count
        )  # Should have 0 pages as still processing
        self.assertEqual(2048, documents[1].size_in_bytes)

    def test_list_documents_empty(self):
        """Test listing documents when no documents exist."""
        # Arrange
        user_id = "test-user-empty"
        self.mock_dynamodb_client.query_by_pk_and_sk_prefix.return_value = []

        # Act
        documents = self.repo.list_documents(user_id)

        # Assert
        self.assertEqual(0, len(documents))
        self.mock_dynamodb_client.query_by_pk_and_sk_prefix.assert_called_once_with(
            pk=f"USER#{user_id}", sk_prefix="PDF#"
        )

    def test_list_documents_error_handling(self):
        """Test error handling when DynamoDB query fails."""
        # Arrange
        user_id = "test-user-error"
        self.mock_dynamodb_client.query_by_pk_and_sk_prefix.side_effect = StorageError(
            message="Test storage error",
            code="test_error",
            details={"user_id": user_id},
        )

        # Act & Assert
        with self.assertRaises(StorageError) as context:
            self.repo.list_documents(user_id)

        self.assertEqual("Test storage error", str(context.exception))
        self.mock_dynamodb_client.query_by_pk_and_sk_prefix.assert_called_once_with(
            pk=f"USER#{user_id}", sk_prefix="PDF#"
        )


if __name__ == "__main__":
    unittest.main()
