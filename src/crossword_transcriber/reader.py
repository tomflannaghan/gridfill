"""Read pipeline: scan image -> 2D array of letters."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

from .classify import classify_cell
from .detection import detect_grid
from .io import ImageSource, load_image
from .preprocess import binarize, to_grayscale
from .recognize import LetterClassifier
from .recognize.cnn import preprocess_cell
from .segmentation import infer_cell_boxes
from .types import CellKind, LetterGrid

_LINE_INK_THRESHOLD = 0.75
_MAX_SCAN_DIVISOR = 4
_BG_PERCENTILE = 85
_BG_BRIGHT_FLOOR = 128


def _strip_border_lines(gray: np.ndarray) -> np.ndarray:
    """White-out residual grid lines / bars along cell edges."""
    h, w = gray.shape[:2]
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    result = gray.copy()
    max_scan = max(3, min(h, w) // _MAX_SCAN_DIVISOR)

    for r in range(max_scan):
        if gray[r].mean() / 255 < _LINE_INK_THRESHOLD:
            result[r, :] = 255
        else:
            break

    for r in range(h - 1, h - 1 - max_scan, -1):
        if gray[r].mean() / 255 < _LINE_INK_THRESHOLD:
            result[r, :] = 255
        else:
            break

    for c in range(max_scan):
        if gray[:, c].mean() / 255 < _LINE_INK_THRESHOLD:
            result[:, c] = 255
        else:
            break

    for c in range(w - 1, w - 1 - max_scan, -1):
        if gray[:, c].mean() / 255 < _LINE_INK_THRESHOLD:
            result[:, c] = 255
        else:
            break

    return result


def _normalize_background(gray: np.ndarray) -> np.ndarray:
    """Shift cell background to white so shaded cells match EMNIST expectations."""
    bg = float(np.percentile(gray, _BG_PERCENTILE))
    if bg >= _BG_BRIGHT_FLOOR:
        return gray
    shifted = gray.astype(np.float32) + (255.0 - bg)
    return np.asarray(np.clip(shifted, 0, 255).astype(np.uint8))


def read_grid(
    source: ImageSource,
    classifier: LetterClassifier | None = None,
    debug_dir: str | os.PathLike[str] | None = None,
) -> LetterGrid:
    """Transcribe a filled crossword scan into a list-of-lists of letters.

    ``None`` marks a block cell, ``""`` an empty white cell (or a letter cell
    when no *classifier* is provided), and ``"A".."Z"`` a recognised letter.

    If *debug_dir* is set, saves each cell's inner crop and its preprocessed
    28x28 image to that directory, named ``R{row}_C{col}_{letter}.png`` and
    ``R{row}_C{col}_{letter}_prep.png``.
    """
    if debug_dir is not None:
        Path(debug_dir).mkdir(parents=True, exist_ok=True)

    image = load_image(source)
    gray = to_grayscale(image)
    detected = detect_grid(binarize(gray))
    boxes = infer_cell_boxes(detected.line_mask)
    rectified = cv2.warpPerspective(gray, detected.transform, detected.size)

    result: LetterGrid = []
    for r, row_boxes in enumerate(boxes):
        row: list[str | None] = []
        for c, box in enumerate(row_boxes):
            cell = rectified[box.y : box.y2, box.x : box.x2]
            kind = classify_cell(cell)

            if kind is CellKind.BLOCK:
                row.append(None)
            elif kind is CellKind.LETTER and classifier is not None:
                clean = _normalize_background(_strip_border_lines(cell))
                prediction = classifier.predict(clean)
                row.append(prediction.letter)
                if debug_dir is not None:
                    tag = f"R{r}_C{c}_{prediction.letter}"
                    cv2.imwrite(str(Path(debug_dir) / f"{tag}.png"), clean)
                    cv2.imwrite(
                        str(Path(debug_dir) / f"{tag}_prep.png"),
                        preprocess_cell(clean),
                    )
            else:
                row.append("")
        result.append(row)
    return result
