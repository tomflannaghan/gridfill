"""Write pipeline: empty grid image + letters -> filled grid image."""

from __future__ import annotations

import os

import numpy as np

from .io import ImageSource
from .types import LetterGrid


def write_grid(
    source: ImageSource,
    letters: LetterGrid,
    out_path: str | os.PathLike[str] | None = None,
    font_path: str | os.PathLike[str] | None = None,
) -> np.ndarray:
    """Render ``letters`` into the cells of an empty grid image.

    Detects and segments the grid, draws each letter centred and sized to fit its
    cell, composites onto a copy of the source, optionally saves to ``out_path``,
    and returns the resulting BGR image array.
    """
    raise NotImplementedError("Phase 2: implement the write pipeline")
