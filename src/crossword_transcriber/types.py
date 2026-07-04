"""Core data types shared across grid detection and the editor."""

from __future__ import annotations

import csv
import io
import os
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
    background: tuple[int, int, int] | None = None


@dataclass
class Grid:
    """A detected and segmented crossword grid.

    Holds the per-cell results plus the perspective transform used to rectify the
    source image, so the same geometry can be reused when rendering back onto it.
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
                    out_row.append(cell.letter or "")
            out.append(out_row)
        return out

    def save_csv(self, path: str | os.PathLike[str]) -> None:
        """Save grid data to a CSV file.

        Format: letters section, blank line, colours section, blank line,
        confidences section.  Block cells are ``#``, empty cells are blank.
        """
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            for row in self.cells:
                w.writerow(_cell_to_letter_field(c) for c in row)
            w.writerow([])
            for row in self.cells:
                w.writerow(_cell_to_colour_field(c) for c in row)
            w.writerow([])
            for row in self.cells:
                w.writerow(_cell_to_confidence_field(c) for c in row)

    @staticmethod
    def load_csv(path: str | os.PathLike[str]) -> Grid:
        """Load a grid from a CSV file written by :meth:`save_csv`.

        The colours and confidences sections are optional — if absent, the grid
        is constructed from letters alone.
        """
        with open(path, newline="") as f:
            sections = _split_csv_sections(f.read())

        if not sections:
            raise ValueError("CSV file contains no data")

        letter_rows = list(csv.reader(io.StringIO(sections[0])))
        colour_rows = list(csv.reader(io.StringIO(sections[1]))) if len(sections) > 1 else None
        conf_rows = list(csv.reader(io.StringIO(sections[2]))) if len(sections) > 2 else None

        nrows = len(letter_rows)
        ncols = len(letter_rows[0]) if nrows else 0

        dummy_box = BoundingBox(0, 0, 0, 0)
        cells: list[list[Cell]] = []
        for r, row in enumerate(letter_rows):
            cell_row: list[Cell] = []
            for c, val in enumerate(row):
                kind, letter = _parse_letter_field(val)
                bg: tuple[int, int, int] | None = None
                if colour_rows and r < len(colour_rows) and c < len(colour_rows[r]):
                    bg = _parse_colour_field(colour_rows[r][c])
                conf: float | None = None
                if conf_rows and r < len(conf_rows) and c < len(conf_rows[r]):
                    conf = _parse_confidence_field(conf_rows[r][c])
                cell_row.append(
                    Cell(
                        row=r,
                        col=c,
                        box=dummy_box,
                        kind=kind,
                        letter=letter,
                        confidence=conf,
                        background=bg,
                    )
                )
            cells.append(cell_row)

        return Grid(rows=nrows, cols=ncols, cells=cells)


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


def _cell_to_confidence_field(cell: Cell) -> str:
    if cell.confidence is not None:
        return f"{cell.confidence:.4f}"
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


def _parse_confidence_field(val: str) -> float | None:
    val = val.strip()
    if not val:
        return None
    return float(val)


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
