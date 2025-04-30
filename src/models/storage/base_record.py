"""Base storage model for DynamoDB records."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseRecord(BaseModel):
    """Base class for DynamoDB records.
    
    Attributes:
        pk: Partition key
        sk: Sort key
        gsi1_pk: Optional GSI1 partition key
        gsi1_sk: Optional GSI1 sort key
        ttl: Optional TTL timestamp
    """
    pk: str = Field(..., description="Partition key")
    sk: str = Field(..., description="Sort key")
    gsi1_pk: Optional[str] = Field(None, description="GSI1 partition key")
    gsi1_sk: Optional[str] = Field(None, description="GSI1 sort key")
    ttl: Optional[int] = Field(None, description="TTL timestamp")

    def to_dynamo(self) -> Dict[str, Any]:
        """Convert record to DynamoDB item format.
        
        Returns:
            Dictionary in DynamoDB item format
        """
        item = self.dict(exclude_none=True)
        return item

    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> Optional["BaseRecord"]:
        """Create record instance from DynamoDB item.
        
        Args:
            item: DynamoDB item dictionary
            
        Returns:
            Record instance or None if item format is invalid
        """
        try:
            # Remove DynamoDB keys
            data = {k: v for k, v in item.items() if k not in ("PK", "SK")}
            return cls(**data)
        except (KeyError, TypeError):
            return None 