"""Image loading helpers.

Images are represented as BGR ``numpy`` arrays (OpenCV's native layout) throughout
the library so the CV modules can use them directly.
"""

from __future__ import annotations

import os

import cv2
import numpy as np
import pypdfium2 as pdfium

# A path-like input, or an already-loaded image array.
ImageSource = str | os.PathLike[str] | np.ndarray

# 300 DPI is enough for an A4-sized scan to print crisply.
_PDF_RENDER_DPI = 300


def _load_pdf(path: str) -> np.ndarray:
    """Render a PDF's last page to a BGR array at print resolution."""
    pdf = pdfium.PdfDocument(path)
    try:
        page = pdf[len(pdf) - 1]
        bitmap = page.render(scale=_PDF_RENDER_DPI / 72)
        return np.asarray(bitmap.to_numpy())[:, :, :3]
    finally:
        pdf.close()


def load_image(source: ImageSource) -> np.ndarray:
    """Load an image as a BGR ``numpy`` array.

    Accepts a filesystem path (including a ``.pdf``, whose last page is
    rendered) or an already-loaded array (returned as-is).
    """
    if isinstance(source, np.ndarray):
        return source
    path = os.fspath(source)
    if path.lower().endswith(".pdf"):
        return _load_pdf(path)
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {path!r}")
    return np.asarray(image)
