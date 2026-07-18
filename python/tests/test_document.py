"""Tests for the .cwd document save/load format."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gridfill.document import load_document, save_document
from gridfill.errors import DocumentError
from gridfill.types import Cell, CellKind, RectangularGrid


def _sample_image() -> np.ndarray:
    image = np.zeros((20, 30, 3), dtype=np.uint8)
    image[:, :] = (10, 20, 30)
    return image


def _sample_grid() -> RectangularGrid:
    cells = [
        Cell(
            polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
            kind=CellKind.LETTER,
            letter="A",
            background=(1, 2, 3),
        ),
        Cell(polygon=[(0.5, 0.0), (1.0, 0.0), (1.0, 0.5), (0.5, 0.5)], kind=CellKind.BLOCK),
    ]
    return RectangularGrid(rows=1, cols=2, cells=cells)


def test_document_round_trip(tmp_path: Path) -> None:
    image = _sample_image()
    grid = _sample_grid()
    annotations = [(0.15, 0.25, "hello")]
    path = tmp_path / "doc.cwd"

    save_document(path, image, [grid], annotations)
    document = load_document(path)

    assert np.array_equal(document.image, image)
    assert document.annotations == annotations
    assert len(document.grids) == 1
    loaded_grid = document.grids[0]
    assert isinstance(loaded_grid, RectangularGrid)
    assert loaded_grid == grid


def test_document_round_trip_no_annotations(tmp_path: Path) -> None:
    path = tmp_path / "doc.cwd"
    save_document(path, _sample_image(), [_sample_grid()], [])
    document = load_document(path)
    assert document.annotations == []


def test_load_document_rejects_wrong_format(tmp_path: Path) -> None:
    path = tmp_path / "bad.cwd"
    path.write_text('{"format": "something-else"}')
    with pytest.raises(DocumentError):
        load_document(path)
