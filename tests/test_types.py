"""Smoke tests for the scaffold: package imports and core type behaviour."""

from __future__ import annotations

import pytest

import gridfill
from gridfill.types import (
    BoundingBox,
    Cell,
    CellKind,
    Grid,
    IrregularGrid,
    RectangularGrid,
    grid_from_dict,
)


def test_public_api_exports() -> None:
    assert hasattr(gridfill, "edit_grid")
    assert gridfill.__version__


def test_bounding_box_corners() -> None:
    box = BoundingBox(x=10, y=20, width=30, height=40)
    assert box.x2 == 40
    assert box.y2 == 60


def test_cell_default_polygon_is_empty() -> None:
    assert Cell().polygon == []


def test_grid_is_abstract() -> None:
    with pytest.raises(TypeError):
        Grid()  # type: ignore[abstract]


def _cell(kind: CellKind, letter: str | None = None) -> Cell:
    return Cell(kind=kind, letter=letter)


def test_grid_to_letters_maps_each_kind() -> None:
    cells = [
        _cell(CellKind.BLOCK),
        _cell(CellKind.EMPTY),
        _cell(CellKind.LETTER, "A"),
    ]
    grid = RectangularGrid(rows=1, cols=3, cells=cells)
    assert grid.to_letters() == [[None, "", "A"]]


def test_rectangular_grid_cell_indexing() -> None:
    cells = [_cell(CellKind.LETTER, letter) for letter in "ABCDEF"]
    grid = RectangularGrid(rows=2, cols=3, cells=cells)
    assert grid.cell(0, 0).letter == "A"
    assert grid.cell(0, 2).letter == "C"
    assert grid.cell(1, 0).letter == "D"
    assert grid.cell(1, 2).letter == "F"


def test_rectangular_grid_bounding_polygon() -> None:
    def poly(x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    cells = [
        Cell(polygon=poly(0.0, 0.0, 0.5, 0.5)),
        Cell(polygon=poly(0.5, 0.0, 1.0, 0.5)),
        Cell(polygon=poly(0.0, 0.5, 0.5, 1.0)),
        Cell(polygon=poly(0.5, 0.5, 1.0, 1.0)),
    ]
    grid = RectangularGrid(rows=2, cols=2, cells=cells)
    assert grid.bounding_polygon() == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def test_cell_round_trips_through_dict() -> None:
    cell = Cell(
        polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
        kind=CellKind.LETTER,
        letter="A",
        background=(10, 20, 30),
    )
    assert Cell.from_dict(cell.to_dict()) == cell


def test_cell_round_trips_with_no_background() -> None:
    cell = Cell(kind=CellKind.BLOCK)
    assert Cell.from_dict(cell.to_dict()) == cell


def test_rectangular_grid_round_trips_through_dict() -> None:
    cells = [_cell(CellKind.LETTER, letter) for letter in "ABCDEF"]
    grid = RectangularGrid(rows=2, cols=3, cells=cells)

    data = grid.to_dict()
    assert data["type"] == "rectangular"

    loaded = grid_from_dict(data)
    assert isinstance(loaded, RectangularGrid)
    assert loaded == grid


def test_irregular_grid_bounding_polygon_is_convex_hull() -> None:
    # Four small cells with a point poking outside their common bounding box; the
    # hull should wrap the outer extent, ignoring interior points.
    cells = [
        Cell(polygon=[(0.0, 0.0), (0.2, 0.0), (0.1, 0.2)]),
        Cell(polygon=[(1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]),
        Cell(polygon=[(0.4, 0.4), (0.5, 0.4), (0.5, 0.5)]),
    ]
    hull = IrregularGrid(cells=cells).bounding_polygon()
    assert set(hull) == {(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)}


def test_irregular_grid_round_trips_through_dict() -> None:
    cells = [
        Cell(polygon=[(0.0, 0.0), (0.1, 0.0), (0.1, 0.1), (0.0, 0.1)], kind=CellKind.EMPTY),
        Cell(polygon=[(0.2, 0.0), (0.3, 0.05), (0.25, 0.15)], kind=CellKind.LETTER, letter="X"),
    ]
    grid = IrregularGrid(cells=cells)

    data = grid.to_dict()
    assert data["type"] == "irregular"

    loaded = grid_from_dict(data)
    assert isinstance(loaded, IrregularGrid)
    assert loaded == grid


def test_grid_from_dict_unknown_type_raises() -> None:
    with pytest.raises(ValueError, match="nonsense"):
        grid_from_dict({"type": "nonsense"})
