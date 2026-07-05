"""Regression tests for irregular-grid detection against real fixtures.

Cells here are arbitrarily shaped (rhombi, hexagons, curved wedges, squares), so
exact cell counts are fragile to segmentation jitter. Assertions are therefore
tolerant: the number of grids is pinned, and each grid's cell count is checked
against a band around the value observed when the detector was tuned.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from gridfill.detection import detect_irregular_grids
from gridfill.preprocess import binarize, to_grayscale
from gridfill.types import IrregularGrid

FIXTURES = Path(__file__).parent / "fixtures"


def _detect(name: str) -> list[IrregularGrid]:
    image = cv2.imread(str(FIXTURES / name))
    assert image is not None, f"missing fixture {name}"
    return detect_irregular_grids(binarize(to_grayscale(image)))


def _avg_vertices(grid: IrregularGrid) -> float:
    return sum(len(c.polygon) for c in grid.cells) / len(grid.cells)


def test_hex_cubes() -> None:
    """A single triangular tessellation of isometric-cube rhombus faces."""
    grids = _detect("irregular_hex.png")
    assert len(grids) == 1
    assert 115 <= len(grids[0].cells) <= 155


def test_stepped_squares() -> None:
    """One square grid with a ragged, stepped boundary. Solid blocked cells have
    no white interior and are legitimately missed, so the band runs low."""
    grids = _detect("irregular_squares.png")
    assert len(grids) == 1
    assert 105 <= len(grids[0].cells) <= 145


def test_wavy_triangle_hexagons() -> None:
    """Four separate hexagons, each split into curved wedge cells."""
    grids = _detect("irregular_wavy_triangle.png")
    assert len(grids) == 4
    for grid in grids:
        assert 15 <= len(grid.cells) <= 21


def test_multigrid_includes_honeycomb() -> None:
    """A mixed page of rectangular grids plus one honeycomb hex grid; irregular
    detection picks up all of them (rectangular grids qualify too, for now)."""
    grids = _detect("irregular_multigrid.png")
    assert len(grids) == 5

    # The honeycomb is the one grid whose cells are hexagonal (many-sided) rather
    # than quadrilateral.
    hex_grids = [g for g in grids if _avg_vertices(g) >= 6]
    assert len(hex_grids) == 1
    assert 125 <= len(hex_grids[0].cells) <= 165


def test_every_cell_has_a_polygon() -> None:
    for name in (
        "irregular_hex.png",
        "irregular_squares.png",
        "irregular_wavy_triangle.png",
        "irregular_multigrid.png",
    ):
        for grid in _detect(name):
            for cell in grid.cells:
                assert len(cell.polygon) >= 3
