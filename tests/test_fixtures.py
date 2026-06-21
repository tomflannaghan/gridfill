"""Regression tests against real scanned crossword fixtures.

These guard the grid-detection backbone on genuine barred scans (clue text,
titles, badges, highlighting, and handwriting outside the grid). Ground-truth
dimensions were confirmed by inspecting the rectified output.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from crossword_transcriber.detection import detect_grid
from crossword_transcriber.preprocess import binarize, to_grayscale
from crossword_transcriber.segmentation import infer_cell_boxes

FIXTURES = Path(__file__).parent / "fixtures"


def _detect_cells(name: str) -> list[list]:
    image = cv2.imread(str(FIXTURES / name))
    assert image is not None, f"missing fixture {name}"
    detected = detect_grid(binarize(to_grayscale(image)))
    return infer_cell_boxes(detected.line_mask)


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
    boxes = _detect_cells(name)
    assert len(boxes) == rows
    assert all(len(row) == cols for row in boxes)
