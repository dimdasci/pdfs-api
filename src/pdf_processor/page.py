"""Module to extract PDF page content and meta-data"""

import pypdfium2 as pdfium

from ..models.domain import Layer, Page, PDFObject, PDFObjectType

# mapping of PDF object types to domain model types
TYPE_NAMES = {
    1: PDFObjectType.TEXT,
    2: PDFObjectType.PATH,
    3: PDFObjectType.IMAGE,
    4: PDFObjectType.SHADE,
    5: PDFObjectType.FORM,
}


def extract_pages(pdf: pdfium.PdfDocument) -> list[Page]:
    """
    Extract pages from the PDF document.

    Args:
        pdf (pdfium.PdfDocument): The PDF document object.

    Returns:
        list[Page]: A list of Page objects containing the extracted page content and meta-data.
    """
    n_pages = len(pdf)
    return [process_page(i + 1, pdf[i]) for i in range(n_pages)]


def get_page_meta(page: pdfium.PdfPage) -> dict:
    """
    Extract meta-data from a PDF page.
    Args:
        page (pdfium.PdfPage): The PDF page object.

    Returns:
        dict: A dictionary containing the extracted page meta-data.
    """

    width, height = page.get_size()
    return {
        "width": width,
        "height": height,
        "rotation": page.get_rotation(),
        "mediabox": page.get_mediabox(),
        "cropbox": page.get_cropbox(),
        "bleedbox": page.get_bleedbox(),
        "trimbox": page.get_trimbox(),
        "artbox": page.get_artbox(),
        "bbox": page.get_bbox(),
    }


def process_page(num: int, page: pdfium.PdfPage) -> Page:
    """
    Process a PDF page and extract objects, grouping them by layer.

    Args:
        page (pdfium.PdfPage): The PDF page object.

    Returns:
        Page: A Page object containing the processed page content and meta-data.
    """
    layers, zero_area_objects = group_by_z_index(page)
    return Page(
        number=num,
        objects=None,
        layers=layers,
        zero_area_objects=zero_area_objects,
        **get_page_meta(page),
    )


def group_by_z_index(page: pdfium.PdfPage) -> tuple[dict[int, Layer], list[PDFObject]]:
    """
    Groups objects by their z-index based on content stream order.

    Args:
      page

    Returns:
        tuple[dict[int, Layer], list[PDFObject]]: A tuple containing:
            - dict[int, Layer] - dictionary of layers by z-index
            - list[PDFObject] - list of zero area objects
    """

    z_index = 0
    z_index_groups = {}
    zero_area_objects: list[PDFObject] = []

    prev_type = None

    for i, obj in enumerate(page.get_objects()):
        bx, by, tx, ty = obj.get_pos()
        if (tx - bx) < 0.0001 or (ty - by) < 0.0001:
            # if object is zero area, we add it to the zero area objects
            zero_area_objects.append(make_object(i, None, obj))
            continue

        # detect change of type
        if obj.type != prev_type:
            z_index += 1

        z_index_groups.setdefault(z_index, []).append(make_object(i, z_index, obj))
        prev_type = obj.type

    # convert to Layer objects
    layers: dict[int, Layer] = {
        z: Layer(z_index=z, type=objects[0].type, objects=objects)
        for z, objects in z_index_groups.items()
        if objects
    }

    return layers, zero_area_objects


def make_object(i: int, z: int, obj: pdfium.PdfObject) -> PDFObject:
    """
    Helper function to create a PDFObject.

    Args:
        i (int): Index of the object.
        z (int): Z-index of the object.
        obj (pdfium.PdfObject): The PDF object.

    Returns:
        PDFObject: The created PDFObject.
    """
    obj_type = TYPE_NAMES.get(obj.type, PDFObjectType.UNKNOWN)
    boundary = obj.get_pos()
    return PDFObject(
        id=i,
        type=obj_type,
        bbox=boundary,
        z_index=z,
        content=obj.page.get_textpage().get_text_bounded(*boundary)[:64]
        if obj_type == PDFObjectType.TEXT
        else None,
    )
