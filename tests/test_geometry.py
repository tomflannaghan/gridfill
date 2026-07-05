"""Phase 1 tests: preprocessing, grid detection, and cell segmentation."""

from __future__ import annotations

import numpy as np
import pytest

from gridfill.detection import detect_grid
from gridfill.errors import GridDetectionError
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


def test_raises_when_no_grid_present() -> None:
    blank = np.full((300, 300, 3), 255, dtype=np.uint8)
    binary = binarize(to_grayscale(blank))
    with pytest.raises(GridDetectionError):
        detect_grid(binary)
