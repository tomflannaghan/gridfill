"""Core data types shared across the read and write pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class CellKind(Enum):
    """What a grid cell contains.

    ``BLOCK`` only occurs in blocked (black-square) crosswords; barred grids use
    only ``EMPTY`` and ``LETTER``.
    """

    BLOCK = "block"
    EMPTY = "empty"
    LETTER = "letter"


@dataclass(frozen=True)
class BoundingBox:
    """An axis-aligned box in rectified-image pixel coordinates."""

    x: int
    y: int
    width: int
    height: int

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height


@dataclass
class Cell:
    """A single grid cell: its position, kind, and (if any) recognised letter."""

    row: int
    col: int
    box: BoundingBox
    kind: CellKind = CellKind.EMPTY
    letter: str | None = None
    confidence: float | None = None


@dataclass
class Grid:
    """A detected and segmented crossword grid.

    Holds the per-cell results plus the perspective transform used to rectify the
    source image, so the same geometry can be reused by the write pipeline.
    """

    rows: int
    cols: int
    cells: list[list[Cell]]
    # 3x3 perspective transform mapping source-image -> rectified coords, or None
    # if the image was already axis-aligned.
    transform: np.ndarray | None = None

    def to_letters(self) -> list[list[str | None]]:
        """Project to the public output format.

        ``None`` for block cells, ``""`` for empty white cells, and the uppercase
        letter otherwise.
        """
        out: list[list[str | None]] = []
        for row in self.cells:
            out_row: list[str | None] = []
            for cell in row:
                if cell.kind is CellKind.BLOCK:
                    out_row.append(None)
                elif cell.kind is CellKind.EMPTY:
                    out_row.append("")
                else:
                    out_row.append(cell.letter)
            out.append(out_row)
        return out


# Public alias for the read/write array format.
LetterGrid = list[list[str | None]]
