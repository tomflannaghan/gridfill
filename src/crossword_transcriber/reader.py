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
from .types import Cell, CellKind, Grid

_LINE_INK_THRESHOLD = 0.75
_MAX_SCAN_DIVISOR = 4
_BG_PERCENTILE = 85
_BG_BRIGHT_FLOOR = 128
_BG_MARGIN_DIVISOR = 6


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


_CORNER_HEIGHT_FRAC = 0.45
_CORNER_WIDTH_FRAC = 0.55


def _remove_corner_clue(gray: np.ndarray) -> np.ndarray:
    """Erase isolated ink blobs in the top-left corner (clue numbers).

    Keeps the largest component (the letter) and removes smaller ones
    whose origin falls inside the corner region.
    """
    h, w = gray.shape[:2]
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
    if n_labels <= 1:
        return gray

    corner_h = int(h * _CORNER_HEIGHT_FRAC)
    corner_w = int(w * _CORNER_WIDTH_FRAC)

    largest_label = int(np.argmax(stats[1:, cv2.CC_STAT_AREA])) + 1
    result = gray.copy()

    for label in range(1, n_labels):
        if label == largest_label:
            continue
        x = stats[label, cv2.CC_STAT_LEFT]
        y = stats[label, cv2.CC_STAT_TOP]
        bw = stats[label, cv2.CC_STAT_WIDTH]
        bh = stats[label, cv2.CC_STAT_HEIGHT]
        if x + bw <= corner_w and y + bh <= corner_h:
            result[labels == label] = 255

    return result


def _normalize_background(gray: np.ndarray) -> np.ndarray:
    """Shift cell background to white so shaded cells match EMNIST expectations."""
    bg = float(np.percentile(gray, _BG_PERCENTILE))
    if bg >= _BG_BRIGHT_FLOOR:
        return gray
    shifted = gray.astype(np.float32) + (255.0 - bg)
    return np.asarray(np.clip(shifted, 0, 255).astype(np.uint8))


def _sample_background(bgr_cell: np.ndarray) -> tuple[int, int, int]:
    """Sample the dominant background BGR color of a cell interior."""
    h, w = bgr_cell.shape[:2]
    margin = max(2, min(h, w) // _BG_MARGIN_DIVISOR)
    inner = bgr_cell[margin : h - margin, margin : w - margin]
    if inner.size == 0:
        return (255, 255, 255)
    if inner.ndim == 3:
        b = int(np.percentile(inner[:, :, 0], _BG_PERCENTILE))
        g = int(np.percentile(inner[:, :, 1], _BG_PERCENTILE))
        r = int(np.percentile(inner[:, :, 2], _BG_PERCENTILE))
        return (b, g, r)
    v = int(np.percentile(inner, _BG_PERCENTILE))
    return (v, v, v)


def read_grid(
    source: ImageSource,
    classifier: LetterClassifier | None = None,
    debug_dir: str | os.PathLike[str] | None = None,
) -> Grid:
    """Transcribe a filled crossword scan into a :class:`Grid`.

    Each cell carries the recognised letter, classifier confidence, and the
    sampled background colour (BGR).  Use :meth:`Grid.to_letters` to obtain the
    simple ``list[list[str | None]]`` format.

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
    rectified_bgr = cv2.warpPerspective(image, detected.transform, detected.size)

    cells: list[list[Cell]] = []
    for r, row_boxes in enumerate(boxes):
        row: list[Cell] = []
        for c, box in enumerate(row_boxes):
            cell_gray = rectified[box.y : box.y2, box.x : box.x2]
            cell_bgr = rectified_bgr[box.y : box.y2, box.x : box.x2]
            kind = classify_cell(cell_gray)

            background = _sample_background(cell_bgr) if kind is not CellKind.BLOCK else None
            letter = None
            confidence = None

            if kind is CellKind.LETTER and classifier is not None:
                clean = _remove_corner_clue(_normalize_background(_strip_border_lines(cell_gray)))
                prediction = classifier.predict(clean)
                letter = prediction.letter
                confidence = prediction.confidence
                if debug_dir is not None:
                    tag = f"R{r}_C{c}_{prediction.letter}"
                    cv2.imwrite(str(Path(debug_dir) / f"{tag}.png"), clean)
                    cv2.imwrite(
                        str(Path(debug_dir) / f"{tag}_prep.png"),
                        preprocess_cell(clean),
                    )

            row.append(
                Cell(
                    row=r,
                    col=c,
                    box=box,
                    kind=kind,
                    letter=letter,
                    confidence=confidence,
                    background=background,
                )
            )
        cells.append(row)

    return Grid(
        rows=len(boxes),
        cols=len(boxes[0]) if boxes else 0,
        cells=cells,
        transform=detected.transform,
    )
