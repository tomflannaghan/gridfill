"""Phase 3 tests: cell classification (block / empty / letter)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from crossword_transcriber.classify import classify_cell
from crossword_transcriber.detection import detect_grid
from crossword_transcriber.preprocess import binarize, to_grayscale
from crossword_transcriber.segmentation import infer_cell_boxes
from crossword_transcriber.types import CellKind

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Unit tests with synthetic cell images
# ---------------------------------------------------------------------------


class TestClassifySynthetic:
    def test_black_cell_is_block(self) -> None:
        cell = np.zeros((40, 40), dtype=np.uint8)
        assert classify_cell(cell) == CellKind.BLOCK

    def test_black_bgr_cell_is_block(self) -> None:
        cell = np.zeros((40, 40, 3), dtype=np.uint8)
        assert classify_cell(cell) == CellKind.BLOCK

    def test_white_cell_is_empty(self) -> None:
        cell = np.full((40, 40), 240, dtype=np.uint8)
        assert classify_cell(cell) == CellKind.EMPTY

    def test_white_cell_with_grid_borders_is_empty(self) -> None:
        """Dark grid-line borders around the edges should be cropped out."""
        cell = np.full((40, 40), 240, dtype=np.uint8)
        cell[:3, :] = 0
        cell[-3:, :] = 0
        cell[:, :3] = 0
        cell[:, -3:] = 0
        assert classify_cell(cell) == CellKind.EMPTY

    def test_central_ink_is_letter(self) -> None:
        cell = np.full((40, 40), 240, dtype=np.uint8)
        cell[12:28, 14:26] = 30
        assert classify_cell(cell) == CellKind.LETTER

    def test_corner_number_is_empty(self) -> None:
        """A small dark mark in the top-left corner (clue number) -> EMPTY."""
        cell = np.full((60, 60), 240, dtype=np.uint8)
        cell[12:22, 12:22] = 30
        assert classify_cell(cell) == CellKind.EMPTY

    def test_letter_plus_corner_number_is_letter(self) -> None:
        """A cell with both a clue number and a letter -> LETTER."""
        cell = np.full((60, 60), 240, dtype=np.uint8)
        cell[12:20, 12:18] = 40  # small corner number
        cell[22:45, 18:42] = 30  # letter in centre
        assert classify_cell(cell) == CellKind.LETTER

    def test_tiny_cell_is_empty(self) -> None:
        cell = np.full((6, 6), 240, dtype=np.uint8)
        assert classify_cell(cell) == CellKind.EMPTY


# ---------------------------------------------------------------------------
# Integration tests on real fixtures
# ---------------------------------------------------------------------------


def _classify_fixture_cells(name: str) -> list[list[CellKind]]:
    """Run detect → segment → classify on a fixture image."""
    image = cv2.imread(str(FIXTURES / name))
    assert image is not None, f"missing fixture {name}"
    gray = to_grayscale(image)
    detected = detect_grid(binarize(gray))
    boxes = infer_cell_boxes(detected.line_mask)
    rectified_gray = cv2.warpPerspective(gray, detected.transform, detected.size)
    result: list[list[CellKind]] = []
    for row in boxes:
        kind_row: list[CellKind] = []
        for box in row:
            cell_crop = rectified_gray[box.y : box.y2, box.x : box.x2]
            kind_row.append(classify_cell(cell_crop))
        result.append(kind_row)
    return result


@pytest.mark.parametrize(
    "name",
    ["barred.png", "barred_very_messy.png", "barred_multiletter_cells.png"],
)
def test_barred_fixtures_have_no_blocks(name: str) -> None:
    """Barred crosswords have no black cells — nothing should classify as BLOCK."""
    kinds = _classify_fixture_cells(name)
    for r, row in enumerate(kinds):
        for c, kind in enumerate(row):
            assert kind != CellKind.BLOCK, f"cell ({r},{c}) in {name} falsely classified as BLOCK"


def test_barred_fixture_all_filled() -> None:
    """A fully-filled barred grid should have every cell classified as LETTER."""
    kinds = _classify_fixture_cells("barred.png")
    for r, row in enumerate(kinds):
        for c, kind in enumerate(row):
            assert kind == CellKind.LETTER, f"cell ({r},{c}) expected LETTER, got {kind}"


def test_empty_synthetic_cells_are_empty() -> None:
    """Cells in an empty (unfilled) grid should all classify as EMPTY."""
    from .synthetic import make_grid

    grid = make_grid(n_rows=3, n_cols=3, cell_px=60, with_clutter=False)
    gray = to_grayscale(grid.image)
    detected = detect_grid(binarize(gray))
    boxes = infer_cell_boxes(detected.line_mask)
    rectified_gray = cv2.warpPerspective(gray, detected.transform, detected.size)
    for r, row in enumerate(boxes):
        for c, box in enumerate(row):
            cell = rectified_gray[box.y : box.y2, box.x : box.x2]
            assert classify_cell(cell) == CellKind.EMPTY, f"cell ({r},{c}) should be EMPTY"
