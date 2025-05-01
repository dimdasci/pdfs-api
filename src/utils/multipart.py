"""Multipart form data parsing utilities.

This module provides utilities for parsing multipart/form-data content
with multiple fallback strategies for robustness.
"""

import io
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union


class MultipartParser:
    """Parse multipart/form-data content with support for both text fields and binary files."""

    def __init__(
        self, content_type: str, body_data: Union[bytes, BinaryIO, io.BytesIO]
    ):
        """Initialize the parser with content type and body data.

        Args:
            content_type: The Content-Type header with boundary information
            body_data: The raw request body as bytes or file-like object
        """
        self.content_type = content_type
        self.body_data = body_data
        self.boundary = self._extract_boundary(content_type)
        self.body_bytes = self._ensure_bytes(body_data)

    def _extract_boundary(self, content_type: str) -> str:
        """Extract boundary string from Content-Type header.

        Args:
            content_type: The Content-Type header

        Returns:
            The boundary string

        Raises:
            ValueError: If boundary is missing from Content-Type
        """
        if "; boundary=" not in content_type:
            raise ValueError("Content-Type missing boundary parameter")

        boundary = content_type.split("; boundary=")[1].strip()
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]  # Remove quotes if present

        return boundary

    def _ensure_bytes(self, data: Union[bytes, BinaryIO, io.BytesIO]) -> bytes:
        """Convert input data to bytes.

        Args:
            data: Input data which could be bytes or file-like object

        Returns:
            The data as bytes
        """
        if hasattr(data, "read"):
            # It's a file-like object
            data.seek(0)
            return data.read()
        # Already bytes
        return data

    def parse(self) -> Dict[str, Any]:
        """Parse multipart form data into dictionary format.

        Returns:
            Dict with form fields and file data
        """
        # Prepare boundary patterns as bytes
        boundary_bytes = f"--{self.boundary}".encode("utf-8")
        boundary_end_bytes = f"--{self.boundary}--".encode("utf-8")

        # Extract parts between boundaries
        parts = self._extract_parts(boundary_bytes, boundary_end_bytes)

        # Process each part into the result dictionary
        result = {}
        for part in parts:
            name, value = self._process_part(part)
            if name:
                result[name] = value

        return result

    def _extract_parts(
        self, boundary_bytes: bytes, boundary_end_bytes: bytes
    ) -> List[bytes]:
        """Extract individual parts from the multipart data.

        Args:
            boundary_bytes: The boundary marker
            boundary_end_bytes: The end boundary marker

        Returns:
            List of parts as bytes
        """
        parts = []
        body_len = len(self.body_bytes)
        start_idx = 0

        # Find each part delimited by boundaries
        while start_idx < body_len:
            # Find next boundary
            next_boundary_idx = self.body_bytes.find(boundary_bytes, start_idx)

            if next_boundary_idx == -1:
                # No more boundaries found
                break

            # Move past the boundary
            start_idx = next_boundary_idx + len(boundary_bytes)

            # Skip the CRLF after boundary
            if (
                start_idx + 2 <= body_len
                and self.body_bytes[start_idx : start_idx + 2] == b"\r\n"
            ):
                start_idx += 2

            # Find the next boundary (regular or end)
            end_part_idx = self.body_bytes.find(boundary_bytes, start_idx)
            if end_part_idx == -1:
                # Check if it's the final boundary
                end_part_idx = self.body_bytes.find(boundary_end_bytes, start_idx)
                if end_part_idx == -1:
                    # If no end boundary either, take all remaining data
                    end_part_idx = body_len
                else:
                    # Adjust to exclude the CRLF before boundary
                    if (
                        end_part_idx >= 2
                        and self.body_bytes[end_part_idx - 2 : end_part_idx] == b"\r\n"
                    ):
                        end_part_idx -= 2
            else:
                # Adjust to exclude the CRLF before boundary
                if (
                    end_part_idx >= 2
                    and self.body_bytes[end_part_idx - 2 : end_part_idx] == b"\r\n"
                ):
                    end_part_idx -= 2

            # Extract part content
            part_content = self.body_bytes[start_idx:end_part_idx]
            if part_content:
                parts.append(part_content)

            # Move to the next part
            start_idx = end_part_idx

        return parts

    def _process_part(self, part: bytes) -> Tuple[Optional[str], Any]:
        """Process a single part from multipart data.

        Args:
            part: The part content as bytes

        Returns:
            Tuple of (field_name, field_value) or (None, None) if invalid
        """
        # Find the divider between headers and content (empty line)
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            return None, None

        # Split headers and content
        headers_bytes = part[:header_end]
        content_bytes = part[header_end + 4 :]  # +4 to skip \r\n\r\n

        # Parse headers into a dictionary
        headers = self._parse_headers(headers_bytes)

        # Extract name and filename from Content-Disposition
        if "content-disposition" not in headers:
            return None, None

        # Parse Content-Disposition to get field name and filename
        name, filename = self._parse_content_disposition(headers["content-disposition"])

        if not name:
            return None, None

        # Process field value based on whether it's a file or text field
        if filename:
            return name, {
                "file_name": filename,
                "content": content_bytes,  # Keep binary content as-is
                "content_type": headers.get("content-type", "application/octet-stream"),
            }
        else:
            # For text fields, convert to string
            try:
                return name, content_bytes.decode("utf-8").strip()
            except UnicodeDecodeError:
                # Fallback if decoding fails
                return name, content_bytes.decode("utf-8", errors="replace").strip()

    def _parse_headers(self, headers_bytes: bytes) -> Dict[str, str]:
        """Parse part headers from bytes into dictionary.

        Args:
            headers_bytes: The headers portion of a part

        Returns:
            Dictionary of header names to values
        """
        headers = {}
        header_lines = headers_bytes.split(b"\r\n")

        for header_line in header_lines:
            if b": " not in header_line:
                continue

            header_name, header_value = header_line.split(b": ", 1)
            try:
                headers[header_name.decode("utf-8").lower()] = header_value.decode(
                    "utf-8"
                )
            except UnicodeDecodeError:
                # Handle binary header values as a fallback
                headers[header_name.decode("utf-8", errors="replace").lower()] = str(
                    header_value
                )

        return headers

    def _parse_content_disposition(
        self, content_disp: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Parse Content-Disposition header to extract name and filename.

        Args:
            content_disp: The Content-Disposition header value

        Returns:
            Tuple of (name, filename), either can be None
        """
        name = None
        filename = None

        # Parse Content-Disposition parameters
        for param in content_disp.split(";"):
            param = param.strip()
            if param.startswith("name="):
                name = param[5:].strip("\"'")
            elif param.startswith("filename="):
                filename = param[9:].strip("\"'")

        return name, filename


class SimpleFormParser:
    """Fallback parser for simple multipart form data when the main parser fails."""

    def __init__(
        self, content_type: str, body_data: Union[bytes, BinaryIO, io.BytesIO]
    ):
        """Initialize the parser with content type and body data.

        Args:
            content_type: The Content-Type header with boundary information
            body_data: The raw request body as bytes or file-like object
        """
        self.content_type = content_type
        self.body_data = body_data

    def parse(self) -> Dict[str, Any]:
        """Parse multipart form data into dictionary format using simple string operations.

        Returns:
            Dict with form fields (but generally without binary data)
        """
        # Convert body to string
        if hasattr(self.body_data, "read"):
            self.body_data.seek(0)
            content_bytes = self.body_data.read()
        else:
            content_bytes = self.body_data

        try:
            content_str = content_bytes.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            # If we can't decode, we can't use this parser
            return {}

        # Extract boundary
        if "; boundary=" not in self.content_type:
            return {}

        boundary = self.content_type.split("boundary=")[1].strip()
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]

        # Parse the multipart data
        result = {}
        parts = content_str.split("--" + boundary)

        for part in parts:
            if "Content-Disposition: form-data; name=" not in part:
                continue

            # Extract name
            name_section = part.split("Content-Disposition: form-data; name=")[1]
            name_end = name_section.find("\r\n")
            if name_end == -1:
                continue

            name = name_section[:name_end].strip("\"'")

            # Check if this is a file
            is_file = "filename=" in part

            # Find the empty line that separates headers from content
            if "\r\n\r\n" in part:
                value = part.split("\r\n\r\n")[1].strip()

                # For simple parsing, we don't handle file uploads properly
                # but we can at least capture the filename
                if is_file:
                    filename_section = part.split("filename=")[1]
                    filename_end = filename_section.find("\r\n")
                    if filename_end == -1:
                        filename = filename_section.strip("\"'")
                    else:
                        filename = filename_section[:filename_end].strip("\"'")

                    result[name] = {
                        "file_name": filename,
                        "content": b"",  # Empty content for fallback
                        "content_type": "application/octet-stream",
                    }
                else:
                    # For text fields, just store the value
                    result[name] = value

        return result


class DirectExtractor:
    """Last-resort extractor that directly looks for known field patterns in the raw data."""

    def __init__(self, body_data: Union[bytes, BinaryIO, io.BytesIO]):
        """Initialize the extractor with body data.

        Args:
            body_data: The raw request body as bytes or file-like object
        """
        self.body_data = body_data

    def extract(self, field_names: List[str]) -> Dict[str, Any]:
        """Extract fields directly from body using pattern matching.

        Args:
            field_names: List of field names to look for

        Returns:
            Dict with any fields that could be extracted
        """
        # Convert to string for pattern matching
        if hasattr(self.body_data, "read"):
            self.body_data.seek(0)
            body_bytes = self.body_data.read()
        else:
            body_bytes = self.body_data

        try:
            body_str = body_bytes.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            return {}

        # Extract fields using string matching
        result = {}

        for field_name in field_names:
            field_pattern = f'name="{field_name}"'
            if field_pattern in body_str:
                parts = body_str.split(field_pattern)
                if len(parts) > 1 and "\r\n\r\n" in parts[1]:
                    value = parts[1].split("\r\n\r\n")[1].split("\r\n")[0]
                    result[field_name] = value

        return result
