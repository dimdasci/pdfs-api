"""DynamoDB implementation of document repository.

This implementation handles direct serialization and deserialization between
domain models and DynamoDB storage format, without intermediate storage models.
"""

import datetime
from decimal import Decimal
from typing import Any, Dict, List

from ..clients.dynamodb import DynamoDBClient
from ..middleware.exceptions.storage import DocumentNotFoundError, StorageGeneralError
from ..models.domain.document import Document, DocumentSource
from ..models.domain.enums import PDFObjectType, ProcessingStatus
from ..models.domain.layer import Layer
from ..models.domain.page import Page
from ..models.domain.pdf_object import PDFObject


class DynamoDBDocumentRepository:
    """DynamoDB implementation of document repository operations.

    This repository handles all database operations related to documents and pages,
    including serialization between domain models and DynamoDB-specific storage format.
    """

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
        return f"PAGE#{document_id}#{page_number:03d}"

    def _serialize_document(self, document: Document) -> Dict[str, Any]:
        """Convert a domain Document to a DynamoDB item.

        Args:
            document: The Document domain object

        Returns:
            Dictionary suitable for DynamoDB storage
        """
        document_item = {
            "type": "DOCUMENT",
            "user_id": document.user_id,
            "document_id": document.id,
            "name": document.name,
            "source": document.source.value
            if hasattr(document.source, "value")
            else str(document.source),
            "source_url": str(document.source_url) if document.source_url else None,
            "status": document.status.value
            if hasattr(document.status, "value")
            else str(document.status),
            "created_at": document.uploaded.isoformat() if document.uploaded else None,
            "size_in_bytes": self._convert_to_dynamodb_type(document.size_in_bytes),
            "page_count": self._convert_to_dynamodb_type(document.page_count),
        }

        # Convert any potential information dict values
        if document.info:
            document_item["info"] = self._convert_to_dynamodb_type(document.info)

        return document_item

    def _deserialize_document(self, item: Dict[str, Any]) -> Document:
        """Convert a DynamoDB item to a domain Document.

        Args:
            item: The DynamoDB item

        Returns:
            Document domain object

        Raises:
            ValueError: If required fields are missing or invalid
        """

        # Verify this is a document item
        if item.get("type") != "DOCUMENT":
            raise ValueError(f"Item is not a document: {item.get('SK', 'Unknown')}")

        # Verify source exists
        source_value = item.get("source")
        if source_value is None:
            raise ValueError(
                f"Missing source field for document: {item.get('document_id', 'Unknown')}"
            )

        # Handle possible UTC timezone indicator 'Z'
        created_at = item.get("created_at")
        if created_at and created_at.endswith("Z"):
            created_at = created_at[:-1] + "+00:00"  # Replace Z with +00:00

        # Process the info field if present - convert Decimal to int or float as needed
        info = None
        if "info" in item:
            info = self._normalize_dynamodb_types(item.get("info"))

        # Create the document object
        return Document(
            id=item.get("document_id", "unknown"),
            user_id=item.get("user_id", "unknown"),
            name=item.get("name", "unknown"),
            source=DocumentSource(source_value),
            source_url=item.get("source_url"),
            status=ProcessingStatus(
                item.get("status", ProcessingStatus.PROCESSING.value)
            ),
            uploaded=datetime.datetime.fromisoformat(created_at)
            if created_at
            else datetime.datetime.now(datetime.timezone.utc),
            page_count=item.get("page_count"),
            size_in_bytes=item.get("size_in_bytes", 0),
            info=info,
        )

    def _serialize_page(
        self, page: Page, user_id: str, document_id: str
    ) -> Dict[str, Any]:
        """Convert a domain Page to a DynamoDB item.

        Args:
            page: The Page domain object
            user_id: User ID who owns the document
            document_id: Document ID the page belongs to

        Returns:
            Dictionary suitable for DynamoDB storage
        """
        # Extract layer information
        layers = []
        for layer in page.layers.values():
            layers.append(
                {
                    "z_index": layer.z_index,
                    "type": layer.type.value
                    if hasattr(layer.type, "value")
                    else str(layer.type),
                    "object_count": len(layer.objects),
                }
            )

        # Extract object information
        objects = []
        for layer in page.layers.values():
            for obj in layer.objects:
                objects.append(
                    {
                        "id": obj.id,
                        "type": obj.type.value
                        if hasattr(obj.type, "value")
                        else str(obj.type),
                        "bbox": self._convert_to_dynamodb_type(obj.bbox),
                        "z_index": obj.z_index or layer.z_index,
                    }
                )

        # Include zero area objects if any
        for obj in page.zero_area_objects:
            objects.append(
                {
                    "id": obj.id,
                    "type": obj.type.value
                    if hasattr(obj.type, "value")
                    else str(obj.type),
                    "bbox": self._convert_to_dynamodb_type(obj.bbox),
                    "z_index": obj.z_index or 0,
                }
            )

        # Create the base item and convert all values to DynamoDB-compatible types
        item = {
            "type": "PageBundle",
            "user_id": user_id,
            "document_id": document_id,
            "page_number": page.number,
            "width": self._convert_to_dynamodb_type(page.width),
            "height": self._convert_to_dynamodb_type(page.height),
            "rotation": self._convert_to_dynamodb_type(page.rotation),
            "mediabox": self._convert_to_dynamodb_type(page.mediabox),
            "cropbox": self._convert_to_dynamodb_type(page.cropbox),
            "bleedbox": self._convert_to_dynamodb_type(page.bleedbox),
            "trimbox": self._convert_to_dynamodb_type(page.trimbox),
            "artbox": self._convert_to_dynamodb_type(page.artbox),
            "bbox": self._convert_to_dynamodb_type(page.bbox),
            "layers": self._convert_to_dynamodb_type(layers),
            "objects": self._convert_to_dynamodb_type(objects),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        return item

    def _deserialize_page(self, item: Dict[str, Any]) -> Page:
        """Convert a DynamoDB item to a domain Page.

        Args:
            item: The DynamoDB item

        Returns:
            Page domain object
        """
        # Create base page
        page = Page(
            number=item.get("page_number", 0),
            width=item.get("width", 0),
            height=item.get("height", 0),
            rotation=item.get("rotation", 0),
            mediabox=item.get("mediabox"),
            cropbox=item.get("cropbox"),
            bleedbox=item.get("bleedbox"),
            trimbox=item.get("trimbox"),
            artbox=item.get("artbox"),
            bbox=item.get("bbox"),
        )

        # Process all objects and organize them into layers
        object_by_layer = {}
        zero_area_objects = []

        for obj_data in item.get("objects", []):
            obj_type = PDFObjectType(obj_data.get("type"))
            z_index = obj_data.get("z_index", 0)

            # Create PDF object
            pdf_object = PDFObject(
                id=obj_data.get("id"),
                type=obj_type,
                bbox=obj_data.get("bbox"),
                z_index=z_index,
                content=obj_data.get("content"),
            )

            # Check if it's a zero area object
            if pdf_object.is_zero_area:
                zero_area_objects.append(pdf_object)
            else:
                # Group by layer
                if z_index not in object_by_layer:
                    object_by_layer[z_index] = {"type": obj_type, "objects": []}
                object_by_layer[z_index]["objects"].append(pdf_object)

        # Create layers from grouped objects
        for z_index, layer_data in object_by_layer.items():
            layer = Layer(z_index=z_index, type=layer_data["type"])
            for obj in layer_data["objects"]:
                layer.add_object(obj)
            page.add_layer(layer)

        # Add zero area objects
        page.zero_area_objects = zero_area_objects

        return page

    def save_document(self, document: Document) -> None:
        """Save a document to DynamoDB.

        Args:
            document: The Document domain object to save

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(document.user_id)
        sk = self.document_sk(document.id)
        document_data = self._serialize_document(document)
        item = {"PK": pk, "SK": sk, **document_data}

        # Apply final conversion to ensure all values are DynamoDB-compatible
        sanitized_item = self._convert_to_dynamodb_type(item)

        try:
            self.dynamodb_client.put_item(sanitized_item)
        except Exception as e:
            raise StorageGeneralError(
                f"Failed to save document: {str(e)}",
                details={
                    "user_id": document.user_id,
                    "document_id": document.id,
                    "error": str(e),
                },
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
        return self._deserialize_document(item)

    def list_documents(self, user_id: str) -> List[Document]:
        """List all documents for a user from DynamoDB.

        Args:
            user_id: The user whose documents to list

        Returns:
            List of Document domain objects

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        pk = self.document_pk(user_id)
        # Query directly for items with SK starting with "PDF#" (document records)
        items = self.dynamodb_client.query_by_pk_and_sk_prefix(pk=pk, sk_prefix="PDF#")

        # Filter for document records only
        document_items = [item for item in items if item.get("type") == "DOCUMENT"]

        # Convert DynamoDB items to domain objects
        try:
            docs = [self._deserialize_document(item) for item in document_items]
            return docs
        except Exception as e:
            # Log the error and re-raise as StorageGeneralError
            raise StorageGeneralError(
                f"Failed to convert document records to domain objects: {str(e)}",
                details={"pk": pk, "error": str(e)},
            )

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
        # Use the batch operation even for a single page for efficiency
        self.save_pages([page], user_id, document_id)

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
        return self._deserialize_page(item)

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

    def save_pages(self, pages: List[Page], user_id: str, document_id: str) -> None:
        """Save multiple pages to DynamoDB using batch operations.

        Args:
            pages: The list of Page objects to save
            user_id: The user who owns the document
            document_id: The document identifier

        Raises:
            StorageGeneralError: If DynamoDB operations fail
        """
        if not pages:
            return

        # Create batch of items to put
        batch_items = []
        pk = self.document_pk(user_id)

        for page in pages:
            sk = self.page_bundle_sk(document_id, page.number)
            page_data = self._serialize_page(page, user_id, document_id)
            page_bundle = {
                "PK": pk,
                "SK": sk,
                **page_data,
            }
            # Apply one final conversion at the top level to ensure all values are DynamoDB-compatible
            sanitized_item = self._convert_to_dynamodb_type(page_bundle)
            batch_items.append(sanitized_item)

        # Use the batch write operation through client
        try:
            self.dynamodb_client.batch_put_items(batch_items)
        except Exception as e:
            # Log more detailed information for debugging
            error_msg = f"Failed to save pages in batch: {str(e)}"
            error_details = {
                "user_id": user_id,
                "document_id": document_id,
                "page_count": len(pages),
                "error": str(e),
            }

            # Enhanced debugging for float conversion errors
            if "Float types are not supported" in str(e):
                # Use our utility to find any float values that might have been missed
                for i, item in enumerate(batch_items):
                    float_paths = self._find_floats(item)
                    if float_paths:
                        error_details[f"floats_in_item_{i}"] = float_paths
                        break  # Just find the first problematic item

                # Also include the stack trace to help pinpoint the issue
                import traceback

                error_details["traceback"] = traceback.format_exc()

            raise StorageGeneralError(error_msg, details=error_details)

    @staticmethod
    def _convert_to_dynamodb_type(value: Any) -> Any:
        """Convert Python values to DynamoDB compatible types.

        Args:
            value: The value to convert

        Returns:
            DynamoDB-compatible value

        Note:
            - Converts floats to Decimals
            - Converts lists/dicts recursively
            - Handles tuples (converting to lists)
            - Handles None values safely
        """
        if value is None:
            return None
        elif isinstance(value, float):
            return Decimal(str(value))
        elif isinstance(value, (list, tuple)):
            return [
                DynamoDBDocumentRepository._convert_to_dynamodb_type(item)
                for item in value
            ]
        elif isinstance(value, dict):
            return {
                k: DynamoDBDocumentRepository._convert_to_dynamodb_type(v)
                for k, v in value.items()
            }
        # Handle integers explicitly to avoid any potential float conversion issues
        elif isinstance(value, int):
            return value
        # Return other scalar values as is (strings, booleans, etc.)
        else:
            return value

    @staticmethod
    def _normalize_dynamodb_types(data):
        """Convert DynamoDB specific types to standard Python types.

        Args:
            data: Data returned from DynamoDB that may contain Decimal types

        Returns:
            Data with Decimal types converted to int or float
        """
        if isinstance(data, Decimal):
            # Convert Decimal to int if it's a whole number, otherwise to float
            if data % 1 == 0:
                return int(data)
            return float(data)
        elif isinstance(data, list):
            return [
                DynamoDBDocumentRepository._normalize_dynamodb_types(item)
                for item in data
            ]
        elif isinstance(data, dict):
            return {
                k: DynamoDBDocumentRepository._normalize_dynamodb_types(v)
                for k, v in data.items()
            }
        else:
            return data

    @staticmethod
    def _find_floats(data, path=""):
        """Debugging utility to find float values in nested data structures.

        Args:
            data: Any Python data structure to inspect
            path: Current path within the structure (used for recursion)

        Returns:
            List of paths where float values were found
        """
        float_paths = []

        if isinstance(data, float):
            float_paths.append(f"{path} = {data}")
        elif isinstance(data, (list, tuple)):
            for i, item in enumerate(data):
                float_paths.extend(
                    DynamoDBDocumentRepository._find_floats(item, f"{path}[{i}]")
                )
        elif isinstance(data, dict):
            for k, v in data.items():
                new_path = f"{path}.{k}" if path else k
                float_paths.extend(DynamoDBDocumentRepository._find_floats(v, new_path))

        return float_paths
