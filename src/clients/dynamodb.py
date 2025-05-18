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

    def _paginated_query(
        self, query_params: Dict[str, Any], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Execute a paginated DynamoDB query, handling the 1MB response limit.

        This internal helper method handles pagination for all DynamoDB queries,
        continuing to fetch results until there are no more or until the limit is reached.

        Args:
            query_params: Dictionary of query parameters to pass to DynamoDB
            limit: Optional maximum number of items to return

        Returns:
            List of items matching the query

        Raises:
            StorageError: If the query operation fails
        """
        try:
            # Handle pagination to get all results (DynamoDB has 1MB response limit)
            items = []
            last_evaluated_key = None

            while True:
                if last_evaluated_key:
                    query_params["ExclusiveStartKey"] = last_evaluated_key

                response = self.table.query(**query_params)
                items.extend(response.get("Items", []))

                # Check if we've reached the specified limit
                if limit and len(items) >= limit:
                    items = items[:limit]  # Trim to exact limit
                    break

                # Check if there are more results to fetch
                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break

            return items

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

    def query_by_pk(self, pk: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query items by partition key only.

        This method handles DynamoDB pagination to fetch all items, even if they exceed
        DynamoDB's 1MB response limit.

        Args:
            pk: Partition key to query
            limit: Optional maximum number of items to return

        Returns:
            List of items matching the query

        Raises:
            StorageError: If the query operation fails
        """
        query_params = {"KeyConditionExpression": Key("PK").eq(pk)}
        if limit:
            query_params["Limit"] = limit

        return self._paginated_query(query_params, limit)

    def query_by_pk_and_sk_prefix(
        self, pk: str, sk_prefix: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Query items by partition key and sort key prefix.

        This method handles DynamoDB pagination to fetch all items, even if they exceed
        DynamoDB's 1MB response limit.

        Args:
            pk: Partition key to query
            sk_prefix: Sort key prefix to match
            limit: Optional maximum number of items to return

        Returns:
            List of items matching the query

        Raises:
            StorageError: If the query operation fails
        """
        key_condition = Key("PK").eq(pk) & Key("SK").begins_with(sk_prefix)
        query_params = {"KeyConditionExpression": key_condition}
        if limit:
            query_params["Limit"] = limit

        return self._paginated_query(query_params, limit)

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
        """Update specific fields of an item.

        Args:
            pk: The partition key
            sk: The sort key
            updates: Dictionary of field names and values to update

        Raises:
            DocumentNotFoundError: If the item does not exist
            StorageError: For other DynamoDB errors
        """
        if not updates:
            return

        # Build update expression and expression attribute values
        update_expressions = []
        expression_attribute_values = {}
        expression_attribute_names = {}

        for field_name, value in updates.items():
            # Use placeholders for all attribute names to handle reserved keywords
            name_placeholder = f"#{field_name}"
            value_placeholder = f":val_{field_name}"

            update_expressions.append(f"{name_placeholder} = {value_placeholder}")
            expression_attribute_values[value_placeholder] = value
            expression_attribute_names[name_placeholder] = field_name

        update_expression = "SET " + ", ".join(update_expressions)

        try:
            self.table.update_item(
                Key={"PK": pk, "SK": sk},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ConditionalCheckFailedException":
                raise DocumentNotFoundError(f"Item with PK={pk} and SK={sk} not found")
            else:
                raise StorageError(
                    f"Failed to update item in DynamoDB: {str(e)}",
                    details={"pk": pk, "sk": sk},
                )
        except Exception as e:
            raise StorageError(
                "Failed to update item in DynamoDB",
                details={"pk": pk, "sk": sk, "error": str(e)},
            )

    def batch_put_items(self, items: List[Dict[str, Any]]) -> None:
        """Put multiple items in DynamoDB using BatchWriteItem.

        This method handles chunking items into 25-item batches as required by DynamoDB.

        Args:
            items: List of items to put

        Raises:
            StorageError: If batch put operation fails
        """
        if not items:
            return

        try:
            # DynamoDB BatchWriteItem can process up to 25 items at once
            # so we need to chunk our items
            chunk_size = 25
            for i in range(0, len(items), chunk_size):
                chunk = items[i : i + chunk_size]

                # Format for BatchWriteItem
                request_items = {
                    self.table.name: [{"PutRequest": {"Item": item}} for item in chunk]
                }

                # Execute batch write
                response = self.dynamodb.batch_write_item(RequestItems=request_items)

                # Check for unprocessed items and retry
                unprocessed = response.get("UnprocessedItems", {})
                retry_count = 0
                max_retries = 3

                while unprocessed and retry_count < max_retries:
                    retry_count += 1
                    logger.warning(
                        f"Found {len(unprocessed.get(self.table.name, []))} unprocessed items, retrying (attempt {retry_count})"
                    )
                    # Exponential backoff would be ideal here, simplified for brevity
                    response = self.dynamodb.batch_write_item(RequestItems=unprocessed)
                    unprocessed = response.get("UnprocessedItems", {})

                if unprocessed:
                    logger.error(
                        f"Failed to process all items in batch after {max_retries} retries",
                        extra={
                            "unprocessed_count": len(
                                unprocessed.get(self.table.name, [])
                            )
                        },
                    )
                    raise StorageError(
                        "Failed to process all items in batch write operation",
                        code="batch_write_incomplete",
                        details={
                            "unprocessed_items": len(
                                unprocessed.get(self.table.name, [])
                            )
                        },
                    )

        except ClientError as e:
            raise StorageError(
                "Failed to perform batch put operation",
                code="batch_put_failed",
                details={"error": str(e)},
            )
        except Exception as e:
            raise StorageError(
                "Unexpected error during batch put operation",
                code="batch_put_unexpected",
                details={"error": str(e)},
            )
