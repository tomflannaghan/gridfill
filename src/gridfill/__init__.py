"""Detect crossword grids in images and edit them interactively.

Public API:

    from gridfill import edit_grid
"""

from __future__ import annotations

from .document import CWD_EXTENSION, Document, load_document, save_document
from .editor import edit_grid
from .errors import DocumentError, GridDetectionError, MultipleGridsError
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
    "DocumentError",
    "Document",
    "save_document",
    "load_document",
    "CWD_EXTENSION",
]
