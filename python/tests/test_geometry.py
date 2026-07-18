"""Phase 1 tests: preprocessing, grid detection, and cell segmentation."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from gridfill.detection import detect_grid
from gridfill.errors import GridDetectionError
from gridfill.geometry import incircle, polygon_centre
from gridfill.preprocess import binarize, to_grayscale
from gridfill.types import Cell, RectangularGrid

from .synthetic import make_grid


def _detect(image: np.ndarray) -> RectangularGrid:
    binary = binarize(to_grayscale(image))
    return detect_grid(binary)


def _corners_px(cell: Cell, image_shape: tuple[int, ...]) -> np.ndarray:
    h, w = image_shape[:2]
    return np.array([(x * w, y * h) for x, y in cell.polygon])


@pytest.mark.parametrize("n_rows,n_cols", [(5, 5), (7, 7), (4, 6)])
def test_segments_into_correct_cell_count(n_rows: int, n_cols: int) -> None:
    grid_img = make_grid(n_rows=n_rows, n_cols=n_cols, cell_px=50)
    grid = _detect(grid_img.image)
    assert grid.rows == n_rows
    assert grid.cols == n_cols


def test_cell_boxes_match_expected_size() -> None:
    grid_img = make_grid(n_rows=5, n_cols=5, cell_px=60)
    grid = _detect(grid_img.image)
    for cell in grid.cells:
        top_left, top_right, bottom_right, bottom_left = _corners_px(cell, grid_img.image.shape)
        width = (
            np.linalg.norm(top_right - top_left) + np.linalg.norm(bottom_right - bottom_left)
        ) / 2
        height = (
            np.linalg.norm(bottom_left - top_left) + np.linalg.norm(bottom_right - top_right)
        ) / 2
        assert abs(width - grid_img.cell_px) <= 5
        assert abs(height - grid_img.cell_px) <= 5


def test_cells_tile_without_overlap() -> None:
    grid_img = make_grid(n_rows=5, n_cols=5, cell_px=60)
    grid = _detect(grid_img.image)
    # Adjacent cells share an edge: each cell's right edge ~= next cell's left edge.
    for r in range(grid.rows):
        for c in range(grid.cols - 1):
            left = _corners_px(grid.cell(r, c), grid_img.image.shape)
            right = _corners_px(grid.cell(r, c + 1), grid_img.image.shape)
            assert np.linalg.norm(left[1] - right[0]) <= 2  # left.TR ~= right.TL
            assert np.linalg.norm(left[2] - right[3]) <= 2  # left.BR ~= right.BL


def test_detection_handles_slight_rotation() -> None:
    import cv2

    grid_img = make_grid(n_rows=5, n_cols=5, cell_px=60)
    h, w = grid_img.image.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), 3.0, 1.0)
    rotated = cv2.warpAffine(grid_img.image, rot, (w, h), borderValue=(255, 255, 255))
    grid = _detect(rotated)
    assert grid.rows == 5
    assert grid.cols == 5


@pytest.mark.parametrize(
    "polygon",
    [
        # Up-pointing triangle: its flat bottom edge lies on the bbox maximum.
        [(20.0, 0.0), (40.0, 40.0), (0.0, 40.0)],
        # Right-pointing triangle: its flat right edge lies on the bbox maximum.
        [(0.0, 0.0), (40.0, 20.0), (0.0, 40.0)],
        # Rhombus (the isometric-cube cell shape).
        [(20.0, 0.0), (40.0, 15.0), (20.0, 30.0), (0.0, 15.0)],
        # Plain square.
        [(0.0, 0.0), (30.0, 0.0), (30.0, 30.0), (0.0, 30.0)],
    ],
)
def test_incircle_centre_is_interior(polygon: list[tuple[float, float]]) -> None:
    """The incircle centre must sit inside the polygon with the full incircle
    fitting within it.

    Regression: a polygon whose far edge lay on the bounding-box maximum used to
    lose its zero border in the distance-transform mask, so the peak (and hence
    the letter anchor) drifted onto that edge instead of the cell interior.
    """
    poly = np.array(polygon, dtype=np.float32)
    cx, cy, diameter = incircle(poly)

    signed = cv2.pointPolygonTest(poly, (cx, cy), True)
    assert signed > 0  # strictly interior, never on an edge
    # The reported incircle genuinely fits: the centre is at least its radius
    # away from every edge (allowing 1px for rasterization).
    assert signed >= diameter / 2 - 1.0


def test_polygon_centre_is_interior_and_normalized() -> None:
    """``polygon_centre`` returns the incircle centre in the polygon's own
    normalized [0, 1] space, strictly inside a concave (L-shaped) cell where the
    vertex mean would fall in the missing corner."""
    # An L-shape: the vertex mean sits near (0.4, 0.4), inside the cut-out notch.
    poly = [(0.0, 0.0), (0.6, 0.0), (0.6, 0.3), (0.3, 0.3), (0.3, 0.6), (0.0, 0.6)]
    cx, cy = polygon_centre(poly)
    assert 0.0 < cx < 1.0
    assert 0.0 < cy < 1.0
    signed = cv2.pointPolygonTest(np.array(poly, dtype=np.float32), (cx, cy), True)
    assert signed > 0  # inside the polygon, not in the notch


def test_raises_when_no_grid_present() -> None:
    blank = np.full((300, 300, 3), 255, dtype=np.uint8)
    binary = binarize(to_grayscale(blank))
    with pytest.raises(GridDetectionError):
        detect_grid(binary)
