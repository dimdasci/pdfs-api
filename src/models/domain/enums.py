"""Domain enums for the PDF Analysis service."""

from enum import Enum


class ProcessingStatus(str, Enum):
    """Document processing status.

    Inherits from str to ensure JSON serialization works correctly.
    """

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    def can_transition_to(self, new_status: "ProcessingStatus") -> bool:
        """Check if current status can transition to new status."""
        # Define valid transitions
        valid_transitions = {
            ProcessingStatus.PROCESSING: {
                ProcessingStatus.COMPLETED,
                ProcessingStatus.FAILED,
            },
            ProcessingStatus.COMPLETED: set(),  # Terminal state
            ProcessingStatus.FAILED: set(),  # Terminal state
        }
        return new_status in valid_transitions.get(self, set())


class PDFObjectType(str, Enum):
    """Type of PDF object.

    Inherits from str to ensure JSON serialization works correctly.
    """

    TEXT = "text"
    PATH = "path"
    IMAGE = "image"
    SHADE = "shade"
    FORM = "form"
    UNKNOWN = "unknown"
