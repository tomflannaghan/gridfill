"""Tests for the editor module (non-GUI logic only)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gridfill.document import save_document
from gridfill.editor import _load_source, click_to_cell
from gridfill.types import Cell, IrregularGrid, Point


def _make_cells(rows: int, cols: int, cell_size: int = 100) -> tuple[list[Cell], tuple[int, int]]:
    img_w, img_h = cols * cell_size, rows * cell_size
    cells: list[Cell] = []
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * cell_size, r * cell_size
            x1, y1 = x0 + cell_size, y0 + cell_size
            polygon: list[Point] = [
                (x0 / img_w, y0 / img_h),
                (x1 / img_w, y0 / img_h),
                (x1 / img_w, y1 / img_h),
                (x0 / img_w, y1 / img_h),
            ]
            cells.append(Cell(polygon=polygon))
    return cells, (img_w, img_h)


class TestClickToCell:
    def test_identity_transform_hit(self) -> None:
        cells, size = _make_cells(3, 3, cell_size=100)
        result = click_to_cell(150.0, 50.0, scale=1.0, image_size=size, cells=cells)
        assert result == 1

    def test_identity_transform_scaled(self) -> None:
        cells, size = _make_cells(3, 3, cell_size=100)
        result = click_to_cell(75.0, 25.0, scale=0.5, image_size=size, cells=cells)
        assert result == 1

    def test_outside_grid(self) -> None:
        cells, size = _make_cells(2, 2, cell_size=100)
        result = click_to_cell(250.0, 250.0, scale=1.0, image_size=size, cells=cells)
        assert result is None

    def test_bottom_right_cell(self) -> None:
        cells, size = _make_cells(3, 3, cell_size=100)
        result = click_to_cell(250.0, 250.0, scale=1.0, image_size=size, cells=cells)
        assert result == 8


def test_load_source_accepts_irregular_document(tmp_path: Path) -> None:
    """The editor loader now opens any grid type -- it used to reject
    non-rectangular grids with NotImplementedError."""
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    grid = IrregularGrid(cells=[Cell(polygon=[(0.1, 0.1), (0.2, 0.1), (0.2, 0.2), (0.1, 0.2)])])
    path = tmp_path / "doc.cwd"
    save_document(path, image, [grid], [])

    _loaded_image, grids, save_path, annotations = _load_source(str(path))
    assert len(grids) == 1
    assert isinstance(grids[0], IrregularGrid)
    assert save_path == str(path)


def test_cli_edit_help() -> None:
    from gridfill.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
