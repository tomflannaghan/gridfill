"""Regression tests for irregular-grid detection against real fixtures.

Cells here are arbitrarily shaped (rhombi, hexagons, curved wedges, squares), so
exact cell counts are fragile to segmentation jitter. Assertions are therefore
tolerant: the number of grids is pinned, and each grid's cell count is checked
against a band around the value observed when the detector was tuned.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from gridfill.detection import detect_grids, detect_irregular_grids
from gridfill.preprocess import binarize, to_grayscale
from gridfill.types import Grid, IrregularGrid, RectangularGrid

from .synthetic import make_brick_grid

FIXTURES = Path(__file__).parent / "fixtures"


def _binary(name: str):
    image = cv2.imread(str(FIXTURES / name))
    assert image is not None, f"missing fixture {name}"
    return binarize(to_grayscale(image))


def _detect(name: str) -> list[IrregularGrid]:
    return detect_irregular_grids(_binary(name))


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


def _bbox(grid: Grid) -> tuple[float, float, float, float]:
    points = grid.bounding_polygon()
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def _boxes_overlap(a: Grid, b: Grid) -> float:
    ax0, ay0, ax1, ay1 = _bbox(a)
    bx0, by0, bx1, by1 = _bbox(b)
    iw = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    ih = max(0.0, min(ay1, by1) - max(ay0, by0))
    return iw * ih


def test_combined_detect_keeps_rectangular_and_nonoverlapping_irregular() -> None:
    """On the mixed page, detect_grids returns the rectangular grids plus the one
    honeycomb that has no rectangular counterpart -- the rectangular grids are not
    also returned as duplicate irregular grids."""
    grids = detect_grids(_binary("irregular_multigrid.png"))
    assert any(isinstance(g, RectangularGrid) for g in grids)
    irregular = [g for g in grids if isinstance(g, IrregularGrid)]
    assert len(irregular) == 1  # just the honeycomb hex

    # No two returned grids cover the same area (dedup worked).
    for i, a in enumerate(grids):
        for b in grids[i + 1 :]:
            assert _boxes_overlap(a, b) == 0.0


def test_combined_detect_on_purely_rectangular_page_has_no_irregular_duplicates() -> None:
    grids = detect_grids(_binary("multigrid.png"))
    assert all(isinstance(g, RectangularGrid) for g in grids)
    assert len(grids) == 6


def test_combined_detect_returns_irregular_when_no_rectangular_grid() -> None:
    grids = detect_grids(_binary("irregular_hex.png"))
    assert len(grids) == 1
    assert isinstance(grids[0], IrregularGrid)


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


@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0, 4.0])
def test_brick_grid_detected_at_different_resolutions(scale: float) -> None:
    """A brick-pattern grid (offset rows, no continuous vertical line across
    rows -- only findable via irregular detection) must be detected whether
    it's rendered at low or high resolution.

    Regression test for a bug where the adjacency-bridging distance was a
    fixed pixel constant tuned for one scan's line thickness: a real scan
    whose grid lines were thicker than that constant (a higher-DPI render, in
    effect) had every cell come out as its own isolated region, so no lattice
    of 4+ adjacent cells was ever found. Rendering the *same* logical grid at
    several pixel scales, with the line thickness scaled proportionally as a
    real higher/lower-DPI render would, reproduces that.
    """
    grid = make_brick_grid(
        n_rows=6,
        n_cols=6,
        cell_w=round(60 * scale),
        cell_h=round(40 * scale),
        pad=round(50 * scale),
        line_thickness=max(1, round(2 * scale)),
    )
    binary = binarize(to_grayscale(grid.image))
    grids = detect_irregular_grids(binary)
    assert len(grids) == 1
    assert len(grids[0].cells) == grid.n_cells
