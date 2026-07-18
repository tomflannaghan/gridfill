"""Detect crossword grids in images and save them as ``.cwd`` documents.

Public API:

    from gridfill import detect_grids, save_document
"""

from __future__ import annotations

from .detection import detect_grids
from .document import CWD_EXTENSION, Document, load_document, save_document
from .errors import DocumentError, GridDetectionError, MultipleGridsError
from .types import (
    Cell,
    CellKind,
    Direction,
    Grid,
    IrregularGrid,
    Point,
    RectangularGrid,
)

__version__ = "0.2.0"

__all__ = [
    "detect_grids",
    "Grid",
    "RectangularGrid",
    "IrregularGrid",
    "Cell",
    "CellKind",
    "Direction",
    "Point",
    "GridDetectionError",
    "MultipleGridsError",
    "DocumentError",
    "Document",
    "save_document",
    "load_document",
    "CWD_EXTENSION",
]
