"""Combined detection across all grid geometries.

:func:`detect_grids` runs the rectangular detector first, then the irregular
one, keeping only the irregular grids that don't overlap a rectangular grid
already found. Rectangular detection is the more precise of the two, so where
both fire on the same lattice (every rectangular grid also reads as a lattice of
adjacent same-size cells) the rectangular result wins and the duplicate
irregular one is dropped.
"""

from __future__ import annotations

import numpy as np

from ..errors import GridDetectionError
from ..types import Grid
from .irregular import detect_irregular_grids
from .rectangle import detect_rectangular_grids

# Two grids are treated as the same lattice when their bounding boxes overlap by
# more than this fraction of the smaller box -- enough to catch a rectangular
# grid re-detected as irregular, without merging genuinely adjacent grids.
_OVERLAP_FRACTION = 0.3


def _bounding_box(grid: Grid) -> tuple[float, float, float, float]:
    """Axis-aligned (x0, y0, x1, y1) of a grid, in normalized source coords."""
    points = grid.bounding_polygon()
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def _overlaps(a: Grid, b: Grid) -> bool:
    """Whether two grids cover substantially the same area of the page."""
    ax0, ay0, ax1, ay1 = _bounding_box(a)
    bx0, by0, bx1, by1 = _bounding_box(b)
    inter_w = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    inter_h = max(0.0, min(ay1, by1) - max(ay0, by0))
    intersection = inter_w * inter_h
    if intersection <= 0.0:
        return False
    smaller = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0))
    return smaller > 0.0 and intersection / smaller > _OVERLAP_FRACTION


def detect_grids(binary: np.ndarray) -> list[Grid]:
    """Detect all crossword grids, rectangular and irregular, in the image.

    Returns the rectangular grids (in reading order) followed by any irregular
    grids that don't overlap one of them. Raises :class:`GridDetectionError`
    only when neither detector finds anything.
    """
    try:
        rectangular = detect_rectangular_grids(binary)
    except GridDetectionError:
        rectangular = []

    try:
        irregular = detect_irregular_grids(binary)
    except GridDetectionError:
        irregular = []

    grids: list[Grid] = list(rectangular)
    grids.extend(
        grid for grid in irregular if not any(_overlaps(grid, kept) for kept in rectangular)
    )
    if not grids:
        raise GridDetectionError("No valid grid found in image")
    return grids
