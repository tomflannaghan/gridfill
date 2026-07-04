"""Core data types shared across grid detection and the editor."""

from __future__ import annotations

import csv
import io
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

Point = tuple[float, float]


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
    """A single grid cell: its shape on the source image, kind, and content.

    ``polygon`` is the ordered list of the cell's vertices as (x, y) fractions
    of the *source* image's (width, height) -- i.e. the image originally
    passed to grid detection, not any internal rectified intermediate. For a
    rectangular cell this is always 4 points in
    ``[top-left, top-right, bottom-right, bottom-left]`` order. A cell carries
    no row/col of its own -- its position within a grid is purely a function
    of where it sits in the owning :class:`Grid`'s ``cells`` list.
    """

    polygon: list[Point] = field(default_factory=list)
    kind: CellKind = CellKind.EMPTY
    letter: str | None = None
    background: tuple[int, int, int] | None = None


class Grid(ABC):
    """Abstract base for any detected grid: an ordered list of cells.

    Concrete subclasses add geometry-specific metadata (e.g.
    :class:`RectangularGrid`'s row/column counts), but every ``Grid`` exposes a
    flat, ordered ``cells`` list so geometry-agnostic code can work with any
    grid shape without caring which subclass it has.
    """

    cells: list[Cell]

    @abstractmethod
    def bounding_polygon(self) -> list[Point]:
        """The grid's own outer boundary, in the same normalized coordinate
        space as :attr:`Cell.polygon`."""


@dataclass
class RectangularGrid(Grid):
    """A grid laid out on a regular row/column lattice.

    ``cells`` is stored in row-major (reading) order; use :meth:`cell` to
    address a specific row and column.
    """

    rows: int
    cols: int
    cells: list[Cell]

    def cell(self, row: int, col: int) -> Cell:
        return self.cells[row * self.cols + col]

    def bounding_polygon(self) -> list[Point]:
        top_left = self.cell(0, 0).polygon[0]
        top_right = self.cell(0, self.cols - 1).polygon[1]
        bottom_right = self.cell(self.rows - 1, self.cols - 1).polygon[2]
        bottom_left = self.cell(self.rows - 1, 0).polygon[3]
        return [top_left, top_right, bottom_right, bottom_left]

    def to_letters(self) -> list[list[str | None]]:
        """Project to the public output format.

        ``None`` for block cells, ``""`` for empty white cells, and the uppercase
        letter otherwise.
        """
        out: list[list[str | None]] = []
        for r in range(self.rows):
            out_row: list[str | None] = []
            for c in range(self.cols):
                cell = self.cell(r, c)
                if cell.kind is CellKind.BLOCK:
                    out_row.append(None)
                elif cell.kind is CellKind.EMPTY:
                    out_row.append("")
                else:
                    out_row.append(cell.letter or "")
            out.append(out_row)
        return out

    def save_csv(self, path: str | os.PathLike[str]) -> None:
        """Save grid data to a CSV file.

        Format: letters section, blank line, colours section. Block cells are
        ``#``, empty cells are blank.
        """
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            for r in range(self.rows):
                w.writerow(_cell_to_letter_field(self.cell(r, c)) for c in range(self.cols))
            w.writerow([])
            for r in range(self.rows):
                w.writerow(_cell_to_colour_field(self.cell(r, c)) for c in range(self.cols))

    @staticmethod
    def load_csv(path: str | os.PathLike[str]) -> RectangularGrid:
        """Load a grid from a CSV file written by :meth:`save_csv`.

        The colours section is optional — if absent, the grid is constructed
        from letters alone. Loaded cells have no associated image, so their
        ``polygon`` is empty.
        """
        with open(path, newline="") as f:
            sections = _split_csv_sections(f.read())

        if not sections:
            raise ValueError("CSV file contains no data")

        letter_rows = list(csv.reader(io.StringIO(sections[0])))
        colour_rows = list(csv.reader(io.StringIO(sections[1]))) if len(sections) > 1 else None

        nrows = len(letter_rows)
        ncols = len(letter_rows[0]) if nrows else 0

        cells: list[Cell] = []
        for r, row in enumerate(letter_rows):
            for c, val in enumerate(row):
                kind, letter = _parse_letter_field(val)
                bg: tuple[int, int, int] | None = None
                if colour_rows and r < len(colour_rows) and c < len(colour_rows[r]):
                    bg = _parse_colour_field(colour_rows[r][c])
                cells.append(Cell(kind=kind, letter=letter, background=bg))

        return RectangularGrid(rows=nrows, cols=ncols, cells=cells)


def _cell_to_letter_field(cell: Cell) -> str:
    if cell.kind is CellKind.BLOCK:
        return "#"
    if cell.letter:
        return cell.letter
    return ""


def _cell_to_colour_field(cell: Cell) -> str:
    if cell.background is not None:
        return f"{cell.background[0]} {cell.background[1]} {cell.background[2]}"
    return ""


def _parse_letter_field(val: str) -> tuple[CellKind, str | None]:
    val = val.strip()
    if val == "#":
        return CellKind.BLOCK, None
    if val == "":
        return CellKind.EMPTY, None
    return CellKind.LETTER, val.upper()


def _parse_colour_field(val: str) -> tuple[int, int, int] | None:
    val = val.strip()
    if not val:
        return None
    parts = val.split()
    if len(parts) != 3:
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


def _split_csv_sections(text: str) -> list[str]:
    """Split CSV text on blank lines into sections."""
    sections: list[str] = []
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.strip() == "":
            if current_lines:
                sections.append("\n".join(current_lines))
                current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append("\n".join(current_lines))
    return sections


# Public alias for the simple letter-array format (see Grid.to_letters).
LetterGrid = list[list[str | None]]
