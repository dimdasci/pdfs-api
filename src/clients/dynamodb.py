"""Client wrapper for DynamoDB operations."""

import os
from typing import Any, Dict, List, Optional

import boto3
from aws_lambda_powertools.logging import Logger
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

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

    def put_item(self, item: Dict[str, Any]) -> None:
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
            # Use ConditionExpression to prevent overwrites - check both PK and SK
            self.table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ConditionalCheckFailedException":
                raise DocumentAlreadyExistsError(
                    f"Document with PK {item.get('PK')} and SK {item.get('SK')} already exists"
                )
            raise StorageError(
                f"Failed to put item in DynamoDB",
                code="put_item_failed",
                details={"error": str(e)},
            )

    def get_item(self, pk: str, sk: str) -> Dict[str, Any]:
        """Get an item from DynamoDB.

        Args:
            pk: Partition key
            sk: Sort key

        Returns:
            Item if found

        Raises:
            DocumentNotFoundError: If item not found
            StorageError: If get operation fails
        """
        try:
            response = self.table.get_item(Key={"PK": pk, "SK": sk})
            item = response.get("Item")
            if not item:
                raise DocumentNotFoundError(
                    document_id=sk,  # SK is PDF#<docId>
                    message=f"Document with PK {pk} and SK {sk} not found",
                )
            return item
        except DocumentNotFoundError:
            raise
        except ClientError as e:
            raise StorageError(
                f"Failed to get item from DynamoDB",
                code="get_item_failed",
                details={"error": str(e)},
            )
        except Exception as e:
            raise StorageError(
                f"Failed to get item from DynamoDB",
                code="get_item_failed",
                details={"error": str(e)},
            )

    def query_by_pk(self, pk: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query items by partition key only."""
        try:
            query_params = {"KeyConditionExpression": Key("PK").eq(pk)}
            if limit:
                query_params["Limit"] = limit
            response = self.table.query(**query_params)
            return response.get("Items", [])
        except ClientError as e:
            raise StorageError(
                f"Failed to query items from DynamoDB",
                code="query_items_failed",
                details={"error": str(e)},
            )
        except Exception as e:
            raise StorageError(
                f"Failed to query items from DynamoDB",
                code="query_items_failed",
                details={"error": str(e)},
            )

    def query_by_pk_and_sk_prefix(
        self, pk: str, sk_prefix: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query items by partition key and sort key prefix."""
        try:
            key_condition = Key("PK").eq(pk) & Key("SK").begins_with(sk_prefix)
            query_params = {"KeyConditionExpression": key_condition}
            if limit:
                query_params["Limit"] = limit
            response = self.table.query(**query_params)
            return response.get("Items", [])
        except ClientError as e:
            raise StorageError(
                f"Failed to query items from DynamoDB",
                code="query_items_failed",
                details={"error": str(e)},
            )
        except Exception as e:
            raise StorageError(
                f"Failed to query items from DynamoDB",
                code="query_items_failed",
                details={"error": str(e)},
            )

    def update_item(
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
                ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ConditionalCheckFailedException":
                raise DocumentNotFoundError(
                    document_id=sk,
                    message=f"Document with PK {pk} and SK {sk} not found",
                )
            raise StorageError(
                f"Failed to update item in DynamoDB",
                code="update_item_failed",
                details={"error": str(e)},
            )
        except Exception as e:
            raise StorageError(
                f"Failed to update item in DynamoDB",
                code="update_item_failed",
                details={"error": str(e)},
            )

    def update_item_fields(self, pk: str, sk: str, updates: Dict[str, Any]) -> None:
        """Update fields in an item in DynamoDB.

        Args:
            pk: Partition key
            sk: Sort key
            updates: Dict of fields to update

        Raises:
            DocumentNotFoundError: If item not found
            StorageError: If update operation fails
        """
        if not updates:
            return
        update_expr = "SET " + ", ".join(f"{k} = :{k}" for k in updates)
        expr_values = {f":{k}": v for k, v in updates.items()}
        try:
            self.table.update_item(
                Key={"PK": pk, "SK": sk},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ConditionalCheckFailedException":
                raise DocumentNotFoundError(
                    document_id=sk,
                    message=f"Document with PK {pk} and SK {sk} not found",
                )
            raise StorageError(
                f"Failed to update item in DynamoDB",
                code="update_item_failed",
                details={"error": str(e)},
            )
        except Exception as e:
            raise StorageError(
                f"Failed to update item in DynamoDB",
                code="update_item_failed",
                details={"error": str(e)},
            )
