"""Infer grid dimensions and per-cell pixel bounds from a rectified grid."""

from __future__ import annotations

import numpy as np

from .types import BoundingBox


def infer_cell_boxes(rectified_binary: np.ndarray) -> list[list[BoundingBox]]:
    """Determine rows/cols and the bounding box of every cell.

    Project the line mask onto the X and Y axes; peaks are grid lines, and the
    gaps between consecutive lines define the cells. Works for blocked and barred
    grids alike since both share a full line lattice.
    """
    raise NotImplementedError("Phase 1: implement projection-based segmentation")
