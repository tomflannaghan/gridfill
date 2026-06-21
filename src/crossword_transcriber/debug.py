"""Visualisation helpers for inspecting each pipeline stage.

Overlays detected grid lines, cell bounds, and predicted letters onto a copy of
the source image for manual debugging.
"""

from __future__ import annotations

import cv2
import numpy as np

from .types import Grid


def draw_cell_boxes(image: np.ndarray, grid: Grid) -> np.ndarray:
    """Return a copy of ``image`` with each cell's bounding box drawn on it."""
    out = image.copy()
    for row in grid.cells:
        for cell in row:
            b = cell.box
            cv2.rectangle(out, (b.x, b.y), (b.x2, b.y2), (0, 255, 0), 1)
    return out
