"""Read handwritten crossword grids from images and write them back.

Public API:

    from crossword_transcriber import read_grid, write_grid
"""

from __future__ import annotations

from .editor import edit_grid
from .reader import read_grid
from .types import BoundingBox, Cell, CellKind, Grid, LetterGrid
from .writer import write_grid

__version__ = "0.1.0"

__all__ = [
    "read_grid",
    "write_grid",
    "edit_grid",
    "Grid",
    "Cell",
    "CellKind",
    "BoundingBox",
    "LetterGrid",
]
