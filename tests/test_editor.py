"""Tests for the editor module (non-GUI logic only)."""

from __future__ import annotations

import numpy as np
import pytest

from crossword_transcriber.editor import click_to_cell
from crossword_transcriber.types import BoundingBox


def _make_boxes(rows: int, cols: int, cell_size: int = 100) -> list[list[BoundingBox]]:
    boxes: list[list[BoundingBox]] = []
    for r in range(rows):
        row: list[BoundingBox] = []
        for c in range(cols):
            row.append(BoundingBox(c * cell_size, r * cell_size, cell_size, cell_size))
        boxes.append(row)
    return boxes


class TestClickToCell:
    def test_identity_transform_hit(self) -> None:
        boxes = _make_boxes(3, 3, cell_size=100)
        transform = np.eye(3, dtype=np.float32)
        result = click_to_cell(150.0, 50.0, scale=1.0, transform=transform, boxes=boxes)
        assert result == (0, 1)

    def test_identity_transform_scaled(self) -> None:
        boxes = _make_boxes(3, 3, cell_size=100)
        transform = np.eye(3, dtype=np.float32)
        result = click_to_cell(75.0, 25.0, scale=0.5, transform=transform, boxes=boxes)
        assert result == (0, 1)

    def test_outside_grid(self) -> None:
        boxes = _make_boxes(2, 2, cell_size=100)
        transform = np.eye(3, dtype=np.float32)
        result = click_to_cell(250.0, 250.0, scale=1.0, transform=transform, boxes=boxes)
        assert result is None

    def test_bottom_right_cell(self) -> None:
        boxes = _make_boxes(3, 3, cell_size=100)
        transform = np.eye(3, dtype=np.float32)
        result = click_to_cell(250.0, 250.0, scale=1.0, transform=transform, boxes=boxes)
        assert result == (2, 2)


def test_cli_edit_help() -> None:
    from crossword_transcriber.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main(["edit", "--help"])
    assert exc_info.value.code == 0
