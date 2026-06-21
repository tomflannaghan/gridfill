"""Read pipeline: scan image -> 2D array of letters."""

from __future__ import annotations

import cv2

from .classify import classify_cell
from .detection import detect_grid
from .io import ImageSource, load_image
from .preprocess import binarize, to_grayscale
from .recognize import LetterClassifier
from .segmentation import infer_cell_boxes
from .types import CellKind, LetterGrid

_BORDER_MARGIN_DIVISOR = 6


def read_grid(
    source: ImageSource,
    classifier: LetterClassifier | None = None,
) -> LetterGrid:
    """Transcribe a filled crossword scan into a list-of-lists of letters.

    ``None`` marks a block cell, ``""`` an empty white cell (or a letter cell
    when no *classifier* is provided), and ``"A".."Z"`` a recognised letter.
    """
    image = load_image(source)
    gray = to_grayscale(image)
    detected = detect_grid(binarize(gray))
    boxes = infer_cell_boxes(detected.line_mask)
    rectified = cv2.warpPerspective(gray, detected.transform, detected.size)

    result: LetterGrid = []
    for row_boxes in boxes:
        row: list[str | None] = []
        for box in row_boxes:
            cell = rectified[box.y : box.y2, box.x : box.x2]
            kind = classify_cell(cell)

            if kind is CellKind.BLOCK:
                row.append(None)
            elif kind is CellKind.LETTER and classifier is not None:
                h, w = cell.shape[:2]
                margin = max(2, min(h, w) // _BORDER_MARGIN_DIVISOR)
                inner = cell[margin : h - margin, margin : w - margin]
                row.append(classifier.predict(inner).letter)
            else:
                row.append("")
        result.append(row)
    return result
