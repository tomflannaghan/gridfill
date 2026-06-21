"""Classify each cell as block, empty, or letter-bearing.

Block detection is optional: barred grids have no blocks, so the default is
"treat as a letter cell" and the block check simply never matches.
"""

from __future__ import annotations

import numpy as np

from .types import CellKind


def classify_cell(cell_image: np.ndarray) -> CellKind:
    """Decide whether a cropped cell is a block, empty, or contains a letter.

    - mostly-black fill  -> ``BLOCK`` (only ever true for blocked grids)
    - very low ink ratio -> ``EMPTY``
    - otherwise          -> ``LETTER``
    """
    raise NotImplementedError("Phase 3: implement cell classification")
