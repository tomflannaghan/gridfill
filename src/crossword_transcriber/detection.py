"""Grid detection and perspective rectification.

Detection is driven purely off the line lattice, which is present in both blocked
and barred grids -- we never rely on black blocks existing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DetectedGrid:
    """The rectified grid image plus the transform that produced it."""

    # Rectified, axis-aligned crop containing just the grid.
    image: np.ndarray
    # 3x3 perspective transform from source -> rectified coords, or None.
    transform: np.ndarray | None


def detect_grid(binary: np.ndarray) -> DetectedGrid:
    """Locate the crossword lattice on the page and rectify it.

    Strategy (see PLAN.md S3.1): extract horizontal/vertical line masks via
    morphology, find the grid-like bounding quad, and warp it to an axis-aligned
    crop.
    """
    raise NotImplementedError("Phase 1: implement lattice-based grid detection")
