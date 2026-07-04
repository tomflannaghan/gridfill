"""Detect crossword grids in images and edit them interactively.

Public API:

    from crossword_transcriber import edit_grid
"""

from __future__ import annotations

from .editor import edit_grid
from .errors import GridDetectionError, MultipleGridsError
from .types import Cell, CellKind, Grid, LetterGrid, Point, RectangularGrid

__version__ = "0.1.0"

__all__ = [
    "edit_grid",
    "Grid",
    "RectangularGrid",
    "Cell",
    "CellKind",
    "Point",
    "LetterGrid",
    "GridDetectionError",
    "MultipleGridsError",
]
