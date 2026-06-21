"""Classify each cell as block, empty, or letter-bearing.

Block detection is optional: barred grids have no blocks, so the default is
"treat as a letter cell" and the block check simply never matches.
"""

from __future__ import annotations

import cv2
import numpy as np

from .types import CellKind

_BLOCK_MEAN_THRESHOLD = 80
_EMPTY_CONTRAST_THRESHOLD = 15
_EMPTY_INK_THRESHOLD = 0.02
_BORDER_MARGIN_DIVISOR = 6
_CORNER_MASK_DIVISOR = 3


def classify_cell(cell_image: np.ndarray) -> CellKind:
    """Decide whether a cropped cell is a block, empty, or contains a letter.

    Accepts a grayscale or BGR cell crop (including grid-line borders on edges).
    An inner margin is cropped to exclude border pixels before analysis.
    """
    gray = cell_image if cell_image.ndim == 2 else cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    margin = max(2, min(h, w) // _BORDER_MARGIN_DIVISOR)
    inner = gray[margin : h - margin, margin : w - margin]

    if inner.size == 0:
        return CellKind.EMPTY

    mean = float(inner.mean())

    if mean < _BLOCK_MEAN_THRESHOLD:
        return CellKind.BLOCK

    if float(inner.std()) < _EMPTY_CONTRAST_THRESHOLD:
        return CellKind.EMPTY

    _, binary = cv2.threshold(inner, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Zero out the top-left corner where clue numbers typically sit so they
    # don't inflate the ink count for otherwise-empty cells.
    ih, iw = binary.shape[:2]
    binary[: ih // _CORNER_MASK_DIVISOR, : iw // _CORNER_MASK_DIVISOR] = 0

    ink_ratio = float(binary.mean()) / 255.0
    if ink_ratio < _EMPTY_INK_THRESHOLD:
        return CellKind.EMPTY

    return CellKind.LETTER
