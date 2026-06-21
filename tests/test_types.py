"""Smoke tests for the scaffold: package imports and core type behaviour."""

from __future__ import annotations

import crossword_transcriber as ct
from crossword_transcriber.types import BoundingBox, Cell, CellKind, Grid


def test_public_api_exports() -> None:
    assert hasattr(ct, "read_grid")
    assert hasattr(ct, "write_grid")
    assert ct.__version__


def test_bounding_box_corners() -> None:
    box = BoundingBox(x=10, y=20, width=30, height=40)
    assert box.x2 == 40
    assert box.y2 == 60


def _cell(row: int, col: int, kind: CellKind, letter: str | None = None) -> Cell:
    return Cell(row=row, col=col, box=BoundingBox(0, 0, 1, 1), kind=kind, letter=letter)


def test_grid_to_letters_maps_each_kind() -> None:
    cells = [
        [
            _cell(0, 0, CellKind.BLOCK),
            _cell(0, 1, CellKind.EMPTY),
            _cell(0, 2, CellKind.LETTER, "A"),
        ]
    ]
    grid = Grid(rows=1, cols=3, cells=cells)
    assert grid.to_letters() == [[None, "", "A"]]
