"""Tests for the .cwd document save/load format."""

from __future__ import annotations

import json
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
            text_color=(4, 5, 6),
        ),
        Cell(polygon=[(0.5, 0.0), (1.0, 0.0), (1.0, 0.5), (0.5, 0.5)], kind=CellKind.BLOCK),
    ]
    return RectangularGrid(rows=1, cols=2, cells=cells)


def test_document_round_trip(tmp_path: Path) -> None:
    image = _sample_image()
    grid = _sample_grid()
    annotations = [(0.15, 0.25, "hello", None), (0.35, 0.45, "world", (7, 8, 9))]
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


def test_load_document_defaults_text_color_for_legacy(tmp_path: Path) -> None:
    """Documents saved before text colour existed load with ``None`` colours."""
    image = _sample_image()
    path = tmp_path / "legacy.cwd"
    save_document(path, image, [_sample_grid()], [(0.15, 0.25, "hello", None)])

    # Strip the text_color / colour fields to mimic a pre-colour document.
    payload = json.loads(path.read_text())
    for grid in payload["grids"]:
        for cell in grid["cells"]:
            cell.pop("text_color", None)
    payload["annotations"] = [[0.15, 0.25, "hello"]]  # 3-element form
    path.write_text(json.dumps(payload))

    document = load_document(path)
    assert document.annotations == [(0.15, 0.25, "hello", None)]
    assert document.grids[0].cells[0].text_color is None


def test_load_document_rejects_wrong_format(tmp_path: Path) -> None:
    path = tmp_path / "bad.cwd"
    path.write_text('{"format": "something-else"}')
    with pytest.raises(DocumentError):
        load_document(path)
