"""
Module to extract PDF document meta-data
"""

import pypdfium2 as pdfium


def extract_meta_data(pdf: pdfium.PdfDocument) -> dict:
    """
    Extract meta-data from the PDF document.

    Args:
        pdf (pdfium.PdfDocument): The PDF document object.

    Returns:
        dict: A dictionary containing the extracted meta-data.
    """
    n_pages = len(pdf)
    labels = [pdf.get_page_label(i) for i in range(n_pages) if pdf.get_page_label(i)]
    toc = [
        {
            "level": i.level,
            "page": i.page_index,
            "n_kids": i.n_kids,
            "title": i.title,
        }
        for i in pdf.get_toc()
    ]

    return {
        "version": pdf.get_version(),
        "form_type": pdf.get_formtype(),
        "pagemode": pdf.get_pagemode(),
        "is_tagged": pdf.is_tagged(),
        "attachment_count": pdf.count_attachments(),
        "page_labels": labels if labels else None,
        "toc": toc if toc else None,
        "meta": pdf.get_metadata_dict(),
    }
