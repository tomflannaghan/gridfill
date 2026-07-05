"""Tests for multi-grid detection and selection."""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from gridfill.detection import detect_grid, detect_rectangular_grids
from gridfill.errors import GridDetectionError, MultipleGridsError
from gridfill.preprocess import binarize, to_grayscale

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
    grids = detect_rectangular_grids(_load_binary("multigrid.png"))
    assert len(grids) == 6


def test_detect_grids_reading_order() -> None:
    grids = detect_rectangular_grids(_load_binary("multigrid.png"))
    for i, (expected_rows, expected_cols) in enumerate(MULTIGRID_EXPECTED):
        assert grids[i].rows == expected_rows, (
            f"grid {i + 1}: expected {expected_rows} rows, got {grids[i].rows}"
        )
        assert grids[i].cols == expected_cols, (
            f"grid {i + 1}: expected {expected_cols} cols, got {grids[i].cols}"
        )


@pytest.mark.parametrize("index", range(1, 7))
def test_detect_grid_index_selects_correct_grid(index: int) -> None:
    binary = _load_binary("multigrid.png")
    grid = detect_grid(binary, grid_index=index)
    expected_rows, expected_cols = MULTIGRID_EXPECTED[index - 1]
    assert grid.rows == expected_rows
    assert grid.cols == expected_cols


def test_multigrid_no_index_raises() -> None:
    with pytest.raises(MultipleGridsError) as exc_info:
        detect_grid(_load_binary("multigrid.png"))
    assert exc_info.value.count == 6


def test_single_grid_no_index_works() -> None:
    grid = detect_grid(_load_binary("barred.png"))
    assert grid.rows == 12
    assert grid.cols == 12


def test_index_out_of_range() -> None:
    with pytest.raises(GridDetectionError, match="out of range"):
        detect_grid(_load_binary("multigrid.png"), grid_index=7)


def test_index_on_single_grid() -> None:
    grid = detect_grid(_load_binary("barred.png"), grid_index=1)
    assert grid.rows == 12
    assert grid.cols == 12


def test_detect_grids_finds_single_column_grids() -> None:
    """single_col_grids.png has a normal grid flanked by two 1-column grids."""
    grids = detect_rectangular_grids(_load_binary("single_col_grids.png"))
    assert [(g.rows, g.cols) for g in grids] == [(10, 1), (10, 16), (10, 1)]


def test_detect_grids_finds_single_column_grids_on_a_wide_page() -> None:
    """The coarse line-extraction kernel scales with the *whole* page's width, not
    a grid's own cell pitch, so a single-column grid's border strokes (only one
    cell pitch long) can fall short of it on a large page even though they clear
    it comfortably on this small fixture -- this is what full-resolution scans
    like a scanned A4 page hit. Pad the fixture with whitespace to reproduce a
    large-page width without changing any grid's cell pitch, and confirm the
    finer, pitch-derived second pass still recovers both single-column grids.
    """
    image = cv2.imread(str(FIXTURES / "single_col_grids.png"))
    assert image is not None
    padded = cv2.copyMakeBorder(image, 0, 0, 700, 700, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    grids = detect_rectangular_grids(binarize(to_grayscale(padded)))
    assert [(g.rows, g.cols) for g in grids] == [(10, 1), (10, 16), (10, 1)]
