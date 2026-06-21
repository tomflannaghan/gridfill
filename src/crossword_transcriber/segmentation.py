"""Infer grid dimensions and per-cell pixel bounds from a rectified grid."""

from __future__ import annotations

import numpy as np

from .errors import GridSegmentationError
from .types import BoundingBox


def _find_line_positions(profile: np.ndarray, min_value: float, min_gap: float) -> list[float]:
    """Locate grid-line centres from a 1-D projection profile.

    Each contiguous run of columns/rows whose projected ink exceeds ``min_value``
    is one grid line; its centre is the run midpoint. Runs whose centres fall
    within ``min_gap`` are merged to absorb thick lines split by anti-aliasing.
    """
    above = profile >= min_value
    positions: list[float] = []
    start: int | None = None
    for i, flag in enumerate(above):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            positions.append((start + i - 1) / 2.0)
            start = None
    if start is not None:
        positions.append((start + len(above) - 1) / 2.0)

    merged: list[float] = []
    for pos in positions:
        if merged and pos - merged[-1] < min_gap:
            merged[-1] = (merged[-1] + pos) / 2.0
        else:
            merged.append(pos)
    return merged


def infer_cell_boxes(rectified_line_mask: np.ndarray) -> list[list[BoundingBox]]:
    """Determine rows/cols and the bounding box of every cell.

    Project the line mask onto the X and Y axes; peaks are grid lines, and the
    gaps between consecutive lines define the cells. Works for blocked and barred
    grids alike since both share a full line lattice.
    """
    height, width = rectified_line_mask.shape[:2]
    mask = (rectified_line_mask > 0).astype(np.float32)
    col_profile = mask.sum(axis=0)  # peaks at vertical lines
    row_profile = mask.sum(axis=1)  # peaks at horizontal lines

    x_lines = _find_line_positions(col_profile, min_value=0.4 * height, min_gap=4.0)
    y_lines = _find_line_positions(row_profile, min_value=0.4 * width, min_gap=4.0)

    if len(x_lines) < 2 or len(y_lines) < 2:
        raise GridSegmentationError(
            f"Too few grid lines: {len(x_lines)} vertical, {len(y_lines)} horizontal"
        )

    boxes: list[list[BoundingBox]] = []
    for r in range(len(y_lines) - 1):
        y0 = int(round(y_lines[r]))
        y1 = int(round(y_lines[r + 1]))
        row: list[BoundingBox] = []
        for c in range(len(x_lines) - 1):
            x0 = int(round(x_lines[c]))
            x1 = int(round(x_lines[c + 1]))
            row.append(BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0))
        boxes.append(row)
    return boxes
