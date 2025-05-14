"""Unit tests for the document list handler."""

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from aws_lambda_powertools.event_handler import APIGatewayHttpResolver

from src.clients.dynamodb import DynamoDBClient
from src.handlers.list import handle_get_documents
from src.middleware.exceptions.api import UnauthorizedError
from src.middleware.exceptions.storage import StorageError
from src.models.domain.document import Document, DocumentSource
from src.models.domain.enums import ProcessingStatus
from src.repositories.dynamodb_document import DynamoDBDocumentRepository


class TestHandleGetDocuments(unittest.TestCase):
    """Test cases for the document list handler."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_app = MagicMock(spec=APIGatewayHttpResolver)
        self.mock_dynamodb_client = MagicMock(spec=DynamoDBClient)
        self.mock_logger = MagicMock()

        # Set up sample data
        self.user_id = "test-user-123"
        self.now = datetime.now(timezone.utc)

        # Configure mock app context
        self.mock_app.context = {"user_id": self.user_id}

        # Create patchers
        self.auth_service_patch = patch("src.handlers.list.AuthenticationService")
        self.repo_patch = patch("src.handlers.list.DynamoDBDocumentRepository")

        # Start patches and get mocks
        self.mock_auth_service_class = self.auth_service_patch.start()
        self.mock_repo_class = self.repo_patch.start()

        # Configure mock instances
        self.mock_auth_service = MagicMock()
        self.mock_repo = MagicMock()

        # Make auth_service_class return our mock instance
        self.mock_auth_service_class.return_value = self.mock_auth_service
        self.mock_repo_class.return_value = self.mock_repo

        # Configure auth service to return our test user_id
        self.mock_auth_service.get_authenticated_user_id.return_value = self.user_id

    def tearDown(self):
        """Tear down test fixtures."""
        # Stop patches
        self.auth_service_patch.stop()
        self.repo_patch.stop()

    def test_handle_get_documents_success(self):
        """Test successful retrieval of documents."""
        # Arrange
        # Create sample documents
        documents = [
            Document(
                id="doc1",
                user_id=self.user_id,
                name="Test Document 1",
                source=DocumentSource.FILE,
                status=ProcessingStatus.COMPLETED,
                uploaded=self.now,
                size_in_bytes=1024,
                page_count=5,
            ),
            Document(
                id="doc2",
                user_id=self.user_id,
                name="Test Document 2",
                source=DocumentSource.URL,
                status=ProcessingStatus.PROCESSING,
                uploaded=self.now,
                size_in_bytes=2048,
                page_count=0,
            ),
        ]

        # Configure mock to return sample documents
        self.mock_repo.list_documents.return_value = documents

        # Act
        response = handle_get_documents(
            app=self.mock_app,
            dynamodb_client=self.mock_dynamodb_client,
            logger=self.mock_logger,
        )

        # Assert
        # Verify auth service was called correctly
        self.mock_auth_service.get_authenticated_user_id.assert_called_once()

        # Verify repository was called with correct user ID
        self.mock_repo.list_documents.assert_called_once_with(self.user_id)

        # Verify response structure and content
        self.assertEqual(2, len(response))

        # Verify first document
        self.assertEqual("doc1", response[0].document_id)
        self.assertEqual("Test Document 1", response[0].name)
        self.assertEqual(ProcessingStatus.COMPLETED, response[0].status)
        self.assertEqual(5, response[0].page_count)
        self.assertEqual(1024, response[0].size_in_bytes)

        # Verify second document
        self.assertEqual("doc2", response[1].document_id)
        self.assertEqual("Test Document 2", response[1].name)
        self.assertEqual(ProcessingStatus.PROCESSING, response[1].status)
        self.assertEqual(0, response[1].page_count)
        self.assertEqual(2048, response[1].size_in_bytes)

    def test_handle_get_documents_empty(self):
        """Test handling empty document list."""
        # Arrange
        # Configure mock to return empty list
        self.mock_repo.list_documents.return_value = []

        # Act
        response = handle_get_documents(
            app=self.mock_app,
            dynamodb_client=self.mock_dynamodb_client,
            logger=self.mock_logger,
        )

        # Assert
        # Verify auth service was called correctly
        self.mock_auth_service.get_authenticated_user_id.assert_called_once()

        # Verify repository was called with correct user ID
        self.mock_repo.list_documents.assert_called_once_with(self.user_id)

        # Verify empty response
        self.assertEqual(0, len(response))

    def test_handle_get_documents_unauthorized(self):
        """Test handling unauthorized error."""
        # Arrange
        # Configure auth service to raise UnauthorizedError
        self.mock_auth_service.get_authenticated_user_id.side_effect = (
            UnauthorizedError(message="Unauthorized access", code="unauthorized_access")
        )

        # Act & Assert
        with self.assertRaises(UnauthorizedError):
            handle_get_documents(
                app=self.mock_app,
                dynamodb_client=self.mock_dynamodb_client,
                logger=self.mock_logger,
            )

    def test_handle_get_documents_storage_error(self):
        """Test handling storage error."""
        # Arrange
        # Configure repository to raise StorageError
        self.mock_repo.list_documents.side_effect = StorageError(
            message="Storage error",
            code="storage_error",
            details={"user_id": self.user_id},
        )

        # Act & Assert
        with self.assertRaises(StorageError):
            handle_get_documents(
                app=self.mock_app,
                dynamodb_client=self.mock_dynamodb_client,
                logger=self.mock_logger,
            )
