"""Image loading and saving helpers.

Images are represented as BGR ``numpy`` arrays (OpenCV's native layout) throughout
the library so the CV modules can use them directly.
"""

from __future__ import annotations

import os

import cv2
import numpy as np

# A path-like input, or an already-loaded image array.
ImageSource = str | os.PathLike[str] | np.ndarray


def load_image(source: ImageSource) -> np.ndarray:
    """Load an image as a BGR ``numpy`` array.

    Accepts a filesystem path or an already-loaded array (returned as-is).
    """
    if isinstance(source, np.ndarray):
        return source
    path = os.fspath(source)
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {path!r}")
    return np.asarray(image)


def save_image(path: str | os.PathLike[str], image: np.ndarray) -> None:
    """Write a BGR ``numpy`` array to disk."""
    if not cv2.imwrite(os.fspath(path), image):
        raise OSError(f"Could not write image: {os.fspath(path)!r}")
