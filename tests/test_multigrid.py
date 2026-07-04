"""Tests for multi-grid detection and selection."""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from crossword_transcriber.detection import detect_grid, detect_grids
from crossword_transcriber.errors import GridDetectionError, MultipleGridsError
from crossword_transcriber.preprocess import binarize, to_grayscale
from crossword_transcriber.segmentation import infer_cell_boxes

FIXTURES = Path(__file__).parent / "fixtures"

MULTIGRID_EXPECTED = [
    (12, 12),
    (13, 13),
    (15, 15),
    (11, 12),
    (6, 6),
    (13, 13),
]


def _load_binary(name: str):
    image = cv2.imread(str(FIXTURES / name))
    assert image is not None, f"missing fixture {name}"
    return binarize(to_grayscale(image))


def test_detect_grids_finds_six() -> None:
    grids = detect_grids(_load_binary("multigrid.png"))
    assert len(grids) == 6


def test_detect_grids_reading_order() -> None:
    grids = detect_grids(_load_binary("multigrid.png"))
    for i, (expected_rows, expected_cols) in enumerate(MULTIGRID_EXPECTED):
        boxes = infer_cell_boxes(grids[i].line_mask)
        assert len(boxes) == expected_rows, (
            f"grid {i + 1}: expected {expected_rows} rows, got {len(boxes)}"
        )
        assert len(boxes[0]) == expected_cols, (
            f"grid {i + 1}: expected {expected_cols} cols, got {len(boxes[0])}"
        )


@pytest.mark.parametrize("index", range(1, 7))
def test_detect_grid_index_selects_correct_grid(index: int) -> None:
    binary = _load_binary("multigrid.png")
    detected = detect_grid(binary, grid_index=index)
    boxes = infer_cell_boxes(detected.line_mask)
    expected_rows, expected_cols = MULTIGRID_EXPECTED[index - 1]
    assert len(boxes) == expected_rows
    assert len(boxes[0]) == expected_cols


def test_multigrid_no_index_raises() -> None:
    with pytest.raises(MultipleGridsError) as exc_info:
        detect_grid(_load_binary("multigrid.png"))
    assert exc_info.value.count == 6


def test_single_grid_no_index_works() -> None:
    detected = detect_grid(_load_binary("barred.png"))
    boxes = infer_cell_boxes(detected.line_mask)
    assert len(boxes) == 12
    assert len(boxes[0]) == 12


def test_index_out_of_range() -> None:
    with pytest.raises(GridDetectionError, match="out of range"):
        detect_grid(_load_binary("multigrid.png"), grid_index=7)


def test_index_on_single_grid() -> None:
    detected = detect_grid(_load_binary("barred.png"), grid_index=1)
    boxes = infer_cell_boxes(detected.line_mask)
    assert len(boxes) == 12
    assert len(boxes[0]) == 12
