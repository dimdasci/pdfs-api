"""Client wrapper for DynamoDB operations."""

import os
from typing import Any, Dict, List, Optional

import boto3
from aws_lambda_powertools.logging import Logger
from boto3.dynamodb.conditions import Key

from ..config.app import AppConfig
from ..middleware.exceptions import (
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    StorageError,
)

logger = Logger()


class DynamoDBClient:
    """Client wrapper for DynamoDB operations."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize DynamoDB client.

        Args:
            config: Application configuration
        """
        self.config = config
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(config.dynamodb_table_name)

    async def put_item(self, item: Dict[str, Any]) -> None:
        """Put an item in DynamoDB.

        Args:
            item: Item to put

        Raises:
            DocumentAlreadyExistsError: If item already exists
            StorageError: If put operation fails
        """

        logger.debug(
            "Putting item in DynamoDB",
            extra={
                "item": item,
                "table": self.table,
                "region": os.getenv("AWS_REGION"),
            },
        )

        try:
            # Use ConditionExpression to prevent overwrites
            self.table.put_item(
                Item=item, ConditionExpression="attribute_not_exists(PK)"
            )
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            raise DocumentAlreadyExistsError(
                f"Document with PK {item['PK']} and SK {item['SK']} already exists"
            )
        except Exception as e:
            raise StorageError(
                f"Failed to put item in DynamoDB",
                code="put_item_failed",
                details={"e": str(e)},
            )

    async def get_item(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        """Get an item from DynamoDB.

        Args:
            pk: Partition key
            sk: Sort key

        Returns:
            Item if found, None otherwise

        Raises:
            StorageError: If get operation fails
        """
        try:
            response = self.table.get_item(Key={"PK": pk, "SK": sk})
            return response.get("Item")
        except Exception as e:
            raise StorageError(
                f"Failed to get item from DynamoDB",
                code="get_item_failed",
                details={"e": str(e)},
            )

    async def query_items(
        self, pk: str, sk_prefix: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query items from DynamoDB.

        Args:
            pk: Partition key
            sk_prefix: Sort key prefix to filter by
            limit: Maximum number of items to return

        Returns:
            List of items

        Raises:
            StorageError: If query operation fails
        """
        try:
            key_condition = Key("PK").eq(pk)
            if sk_prefix:
                key_condition = key_condition & Key("SK").begins_with(sk_prefix)

            query_params = {"KeyConditionExpression": key_condition}
            if limit:
                query_params["Limit"] = limit

            response = self.table.query(**query_params)
            return response.get("Items", [])
        except Exception as e:
            raise StorageError(
                f"Failed to query items from DynamoDB",
                code="query_items_failed",
                details={"e": str(e)},
            )

    async def update_item(
        self,
        pk: str,
        sk: str,
        update_expression: str,
        expression_values: Dict[str, Any],
    ) -> None:
        """Update an item in DynamoDB.

        Args:
            pk: Partition key
            sk: Sort key
            update_expression: Update expression
            expression_values: Expression values

        Raises:
            DocumentNotFoundError: If item not found
            StorageError: If update operation fails
        """
        try:
            self.table.update_item(
                Key={"PK": pk, "SK": sk},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(PK)",
            )
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            raise DocumentNotFoundError(f"Document with PK {pk} and SK {sk} not found")
        except Exception as e:
            raise StorageError(
                f"Failed to update item in DynamoDB",
                code="update_item_failed",
                details={"e": str(e)},
            )
