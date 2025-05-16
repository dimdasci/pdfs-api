"""Module to render PDF pages to images"""

from pathlib import Path

import pypdfium2 as pdfium
from PIL.Image import Image
from pypdfium2.raw import FPDFBitmap_BGRA

from ..models.domain import Page


def render_layer(
    file: Path, page_idx: int, start: int, end: int, scale: int = 1
) -> Image:
    """
    Renders a specific layer of a PDF page to an image.

    Args:
        file (Path): The path to the PDF file.
        page_idx (int): The index of the page to render.
        start (int): The starting index of the objects to render.
        end (int): The ending index of the objects to render.
        scale (int, optional): The scale factor for rendering. Defaults to 1.

    Returns:
        Image: The rendered PIL image of the specified layer.
        Raises:
            ValueError: If the start index is greater than the end index.
    """

    temp_doc = pdfium.PdfDocument(file)
    temp_page = temp_doc[page_idx]

    create_layer(temp_page, start, end)
    img = (
        temp_page.render(
            scale=scale,
            fill_color=(0, 0, 0, 0),  # transparent background
            force_bitmap_format=FPDFBitmap_BGRA,
        )
        .to_pil()
        .convert("RGBA")
    )

    # Clean up
    temp_doc = None

    return img


def render_page(file: Path, page: int, scale: float) -> Image:
    """
    Renders a PDF page to an image.

    Args:
        file (Path): The path to the PDF file.
        page (int): The index of the page to render.
        scale (float): The scale factor for rendering.

    Returns:
        Image: The rendered PIL image of the page.
    """

    temp_doc = pdfium.PdfDocument(file)

    bitmap = temp_doc[page].render(
        scale=scale,
        draw_annots=True,
        prefer_bgrx=True,
    )

    # Clean up
    temp_doc = None

    return bitmap.to_pil().convert("RGBA")


def create_layer(page: pdfium.PdfPage, start: int, end: int) -> pdfium.PdfPage:
    """
    Removes all objects from the page except one from start to end inclusive.

    Args:
        page (pdfium.PdfPage): The PDF page object.
        start (int): The starting index of the objects to keep.
        end (int): The ending index of the objects to keep.
    Returns:
        pdfium.PdfPage: The modified PDF page object with the specified objects removed.
    Raises:
        ValueError: If the start index is greater than the end index.
    """

    if start > end:
        raise ValueError("Start index must be less than or equal to end index.")

    objs = list(page.get_objects(max_depth=5))
    objs_to_remove = objs[:start] + objs[end + 1 :]

    for obj in objs_to_remove:
        page.remove_obj(obj)
    page.gen_content()

    return page


def render_pages(
    pdf_file: Path, working_dir: Path, pages: list[Page], scale: int = 1
) -> None:
    """
    Renders all pages of the PDF document py layer and saves them as images.

    Args:
        pdf_file (Path): The path to the PDF file.
        working_dir (Path): The directory where the PDF document is located.
        pages (list[Page]): A list of Page objects.
        scale (int, optional): The scale factor for rendering. Defaults to 1.
    """

    dir = working_dir / "pages"

    for page in pages:
        page_dir = dir / f"p{page.number:03d}"
        page_dir.mkdir(parents=True, exist_ok=True)

        # render and save the page
        page_file = page_dir / "page.png"
        render_page(pdf_file, page.number - 1, scale).save(page_file)

        # render and save the layers
        for z_idx, layer in page.layers.items():
            layer_file = page_dir / f"l{z_idx:03d}.png"

            render_layer(
                pdf_file,
                page.number - 1,
                layer.objects[0].id,
                layer.objects[-1].id,
                scale,
            ).save(layer_file)
