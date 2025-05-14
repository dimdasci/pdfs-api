"""Unit tests for the DynamoDB client."""

import unittest
from unittest.mock import MagicMock, patch

import boto3
from aws_lambda_powertools.logging import Logger
from boto3.dynamodb.conditions import Key

from src.clients.dynamodb import DynamoDBClient
from src.config.app import AppConfig
from src.middleware.exceptions.storage import StorageError


class TestDynamoDBClient(unittest.TestCase):
    """Test cases for the DynamoDB client."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock AppConfig
        self.mock_config = MagicMock(spec=AppConfig)
        self.mock_config.dynamodb_table_name = "test-documents-table"

        # Mock boto3 DynamoDB resource and table
        self.table_patch = patch("boto3.resource")
        self.mock_boto3_resource = self.table_patch.start()
        self.mock_table = MagicMock()

        # Configure the resource mock to return our mock table
        self.mock_resource = MagicMock()
        self.mock_boto3_resource.return_value = self.mock_resource
        self.mock_resource.Table.return_value = self.mock_table

        # Create the client with mocked dependencies
        self.client = DynamoDBClient(self.mock_config)

    def tearDown(self):
        """Tear down test fixtures."""
        self.table_patch.stop()

    def test_paginated_query_single_page(self):
        """Test _paginated_query when all results fit in a single page."""
        # Arrange
        items = [
            {"PK": "USER#123", "SK": "PDF#doc1"},
            {"PK": "USER#123", "SK": "PDF#doc2"},
        ]

        # Configure mock to return a single page of results
        self.mock_table.query.return_value = {
            "Items": items,
            # No LastEvaluatedKey means no more pages
        }

        # Query parameters
        query_params = {"KeyConditionExpression": Key("PK").eq("USER#123")}

        # Act
        result = self.client._paginated_query(query_params)

        # Assert
        # Verify query was called with the expected parameters
        self.mock_table.query.assert_called_once_with(**query_params)

        # Verify result contains all items
        self.assertEqual(items, result)

    def test_paginated_query_multiple_pages(self):
        """Test _paginated_query with multiple pages of results."""
        # Arrange
        # Items for the first page
        items_page1 = [
            {"PK": "USER#123", "SK": "PDF#doc1"},
            {"PK": "USER#123", "SK": "PDF#doc2"},
        ]

        # Items for the second page
        items_page2 = [
            {"PK": "USER#123", "SK": "PDF#doc3"},
            {"PK": "USER#123", "SK": "PDF#doc4"},
        ]

        # Configure mock to return multiple pages
        self.mock_table.query.side_effect = [
            {
                "Items": items_page1,
                "LastEvaluatedKey": {"PK": "USER#123", "SK": "PDF#doc2"},
            },
            {
                "Items": items_page2
                # No LastEvaluatedKey means no more pages
            },
        ]

        # Query parameters
        query_params = {"KeyConditionExpression": Key("PK").eq("USER#123")}

        # Act
        result = self.client._paginated_query(query_params)

        # Assert
        # Verify query was called twice with the expected parameters
        first_call_args = query_params
        second_call_args = {
            **query_params,
            "ExclusiveStartKey": {"PK": "USER#123", "SK": "PDF#doc2"},
        }

        # Check that query was called twice with the correct arguments
        self.assertEqual(2, self.mock_table.query.call_count)
        self.mock_table.query.assert_any_call(**first_call_args)
        self.mock_table.query.assert_any_call(**second_call_args)

        # Verify result contains all items from both pages
        expected_items = items_page1 + items_page2
        self.assertEqual(expected_items, result)

    def test_paginated_query_with_limit(self):
        """Test _paginated_query with a specified limit."""
        # Arrange
        items = [
            {"PK": "USER#123", "SK": "PDF#doc1"},
            {"PK": "USER#123", "SK": "PDF#doc2"},
        ]

        # Configure mock to return results
        self.mock_table.query.return_value = {
            "Items": items,
            # No LastEvaluatedKey means no more pages
        }

        # Query parameters with limit
        query_params = {"KeyConditionExpression": Key("PK").eq("USER#123"), "Limit": 10}

        # Act
        result = self.client._paginated_query(query_params, limit=10)

        # Assert
        # Verify query was called with the expected parameters
        self.mock_table.query.assert_called_once_with(**query_params)

        # Verify result contains all items
        self.assertEqual(items, result)

    def test_paginated_query_error_handling(self):
        """Test _paginated_query handles DynamoDB errors correctly."""
        # Arrange
        # Configure mock to raise an exception
        self.mock_table.query.side_effect = Exception("DynamoDB query failed")

        # Query parameters
        query_params = {"KeyConditionExpression": Key("PK").eq("USER#123")}

        # Act & Assert
        with self.assertRaises(StorageError):
            self.client._paginated_query(query_params)

    def test_query_by_pk(self):
        """Test query_by_pk calls _paginated_query with correct parameters."""
        # Arrange
        # Mock the _paginated_query method
        self.client._paginated_query = MagicMock()

        # Configure mock to return sample items
        sample_items = [
            {"PK": "USER#123", "SK": "PDF#doc1"},
            {"PK": "USER#123", "SK": "PDF#doc2"},
        ]
        self.client._paginated_query.return_value = sample_items

        # Act
        result = self.client.query_by_pk(pk="USER#123", limit=10)

        # Assert
        # Check that _paginated_query was called
        self.client._paginated_query.assert_called_once()

        # Get the actual call arguments
        call_args, call_kwargs = self.client._paginated_query.call_args

        # Verify the first argument (query_params)
        actual_query_params = call_args[0]
        self.assertIn("KeyConditionExpression", actual_query_params)
        self.assertIn("Limit", actual_query_params)
        self.assertEqual(10, actual_query_params["Limit"])

        # Verify the second argument (limit)
        self.assertEqual(10, call_args[1])

        # Verify result
        self.assertEqual(sample_items, result)

    def test_query_by_pk_and_sk_prefix(self):
        """Test query_by_pk_and_sk_prefix calls _paginated_query with correct parameters."""
        # Arrange
        # Mock the _paginated_query method
        self.client._paginated_query = MagicMock()

        # Configure mock to return sample items
        sample_items = [
            {"PK": "USER#123", "SK": "PDF#doc1#PAGE#001"},
            {"PK": "USER#123", "SK": "PDF#doc1#PAGE#002"},
        ]
        self.client._paginated_query.return_value = sample_items

        # Act
        result = self.client.query_by_pk_and_sk_prefix(
            pk="USER#123", sk_prefix="PDF#doc1#PAGE#", limit=10
        )

        # Assert
        # Check that _paginated_query was called
        self.client._paginated_query.assert_called_once()

        # Get the actual call arguments
        call_args, call_kwargs = self.client._paginated_query.call_args

        # Verify the first argument (query_params)
        actual_query_params = call_args[0]
        self.assertIn("KeyConditionExpression", actual_query_params)
        self.assertIn("Limit", actual_query_params)
        self.assertEqual(10, actual_query_params["Limit"])

        # Verify the second argument (limit)
        self.assertEqual(10, call_args[1])

        # Verify result
        self.assertEqual(sample_items, result)
