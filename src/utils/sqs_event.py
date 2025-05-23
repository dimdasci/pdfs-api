"""S3 SQS Event Processor Module"""

import json
from typing import Iterator
from urllib.parse import unquote_plus

from aws_lambda_powertools.utilities.data_classes import SQSEvent


def parser(event: SQSEvent) -> Iterator[dict]:
    """
    Parse the SQS event to extract S3 object keys.

    Args:
        event (SQSEvent): The SQS event containing records.

    Returns:
        Iterator[dict]: An iterator of dictionaries containing the object info with decoded keys.

    Raises:
        ValueError: If the S3 object is not found in the event.
        json.JSONDecodeError: If the JSON decoding fails.
    """

    for record in event.records:
        body = json.loads(record.body)
        # Extract the S3 object key from the event
        for s3_record in body["Records"]:
            if "s3" not in s3_record:
                raise ValueError("S3 record not found in the event")
            obj = s3_record["s3"].get("object")
            if not obj:
                raise ValueError("S3 object not found in the event")
            # Decode the URL-encoded key
            if "key" in obj:
                obj["key"] = unquote_plus(obj["key"])
            yield obj
