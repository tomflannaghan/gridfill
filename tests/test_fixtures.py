"""Regression tests against real scanned crossword fixtures.

These guard the grid-detection backbone on genuine barred scans (clue text,
titles, badges, highlighting, and handwriting outside the grid). Ground-truth
dimensions were confirmed by inspecting the rectified output.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from inkwell.detection import detect_grid
from inkwell.preprocess import binarize, to_grayscale
from inkwell.types import RectangularGrid

FIXTURES = Path(__file__).parent / "fixtures"


def _detect(name: str) -> RectangularGrid:
    image = cv2.imread(str(FIXTURES / name))
    assert image is not None, f"missing fixture {name}"
    return detect_grid(binarize(to_grayscale(image)))


@pytest.mark.parametrize(
    "name,rows,cols",
    [
        ("barred.png", 12, 12),
        ("barred_multiletter_cells.png", 15, 15),
        # Heavy handwriting streaks across cells, yet segmentation recovers the
        # exact (non-square) 11x12 grid.
        ("barred_very_messy.png", 11, 12),
    ],
)
def test_fixtures_detect_exact_grid(name: str, rows: int, cols: int) -> None:
    grid = _detect(name)
    assert grid.rows == rows
    assert grid.cols == cols
