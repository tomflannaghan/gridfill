"""Phase 1 tests: preprocessing, grid detection, and cell segmentation."""

from __future__ import annotations

import numpy as np
import pytest

from crossword_transcriber.detection import detect_grid
from crossword_transcriber.errors import GridDetectionError
from crossword_transcriber.preprocess import binarize, to_grayscale
from crossword_transcriber.segmentation import infer_cell_boxes

from .synthetic import make_grid


def _pipeline(image: np.ndarray):
    binary = binarize(to_grayscale(image))
    detected = detect_grid(binary)
    return detected, infer_cell_boxes(detected.line_mask)


@pytest.mark.parametrize("n_rows,n_cols", [(5, 5), (7, 7), (4, 6)])
def test_segments_into_correct_cell_count(n_rows: int, n_cols: int) -> None:
    grid = make_grid(n_rows=n_rows, n_cols=n_cols, cell_px=50)
    _, boxes = _pipeline(grid.image)
    assert len(boxes) == n_rows
    assert all(len(row) == n_cols for row in boxes)


def test_cell_boxes_match_expected_size() -> None:
    grid = make_grid(n_rows=5, n_cols=5, cell_px=60)
    detected, boxes = _pipeline(grid.image)
    # Rectified width should be close to the true grid width.
    assert abs(detected.size[0] - grid.n_cols * grid.cell_px) <= 4
    for row in boxes:
        for box in row:
            assert abs(box.width - grid.cell_px) <= 5
            assert abs(box.height - grid.cell_px) <= 5


def test_cells_tile_without_overlap() -> None:
    grid = make_grid(n_rows=5, n_cols=5, cell_px=60)
    _, boxes = _pipeline(grid.image)
    # Adjacent cells share an edge: each cell's x2 ~ next cell's x.
    for row in boxes:
        for left, right in zip(row, row[1:], strict=False):
            assert abs(left.x2 - right.x) <= 2


def test_detection_handles_slight_rotation() -> None:
    import cv2

    grid = make_grid(n_rows=5, n_cols=5, cell_px=60)
    h, w = grid.image.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), 3.0, 1.0)
    rotated = cv2.warpAffine(grid.image, rot, (w, h), borderValue=(255, 255, 255))
    binary = binarize(to_grayscale(rotated))
    detected = detect_grid(binary)
    boxes = infer_cell_boxes(detected.line_mask)
    assert len(boxes) == 5
    assert all(len(row) == 5 for row in boxes)


def test_raises_when_no_grid_present() -> None:
    blank = np.full((300, 300, 3), 255, dtype=np.uint8)
    binary = binarize(to_grayscale(blank))
    with pytest.raises(GridDetectionError):
        detect_grid(binary)
