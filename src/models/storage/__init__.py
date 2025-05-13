"""Storage models for the PDF Analysis service."""

from .document_record import DocumentRecord
from .page_bundle_record import PageBundleRecord

__all__ = [
    "DocumentRecord",
    "PageBundleRecord",
]
