from pathlib import Path

import pypdfium2 as pdfium

from ..models.domain import Document, Page
from .document import extract_meta_data
from .page import extract_pages
from .render import render_pages

ORIGINAL_PDF_FILE_NAME = "original.pdf"


def process_pdf(working_dir: Path, document: Document) -> Document:
    """
    Process the PDF document located in the working directory and returns processed one.

    Extract PDF related document meta-data, process all pages and extracts objects, grouping them by layer.

    Args:
        working_dir (Path): The directory where the PDF document is located.
        document (Document): The document object containing initial document meta-data.

    Returns:
        Document: The processed document object with the updated file name.
    """

    file = working_dir / ORIGINAL_PDF_FILE_NAME
    if not file.exists():
        raise FileNotFoundError(f"File {file} does not exist.")

    pdf = None  # Initialize pdf to None
    try:
        # Read the PDF file
        pdf = pdfium.PdfDocument(file)
        meta = extract_meta_data(pdf)
        pages: list[Page] = extract_pages(pdf)
    finally:
        if pdf:
            pdf.close()  # Explicitly close the document

    # render pages
    render_pages(file, working_dir, pages)

    return document.model_copy(
        update={"page_count": len(pages), "pages": pages, "info": meta}
    )
