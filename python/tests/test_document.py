"""Tests for the .cwd document save/load format."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from gridfill.document import (
    CurveAnnotation,
    LineAnnotation,
    TextAnnotation,
    load_document,
    save_document,
)
from gridfill.errors import DocumentError
from gridfill.types import Cell, CellKind, RectangularGrid


def _sample_image() -> np.ndarray:
    image = np.zeros((20, 30, 3), dtype=np.uint8)
    image[:, :] = (10, 20, 30)
    return image


def _sample_grid() -> RectangularGrid:
    cells = [
        Cell(
            polygon=[(0.0, 0.0), (15.0, 0.0), (15.0, 10.0), (0.0, 10.0)],
            kind=CellKind.LETTER,
            letter="A",
            background=(1, 2, 3),
            text_colour=(4, 5, 6),
        ),
        Cell(polygon=[(15.0, 0.0), (30.0, 0.0), (30.0, 10.0), (15.0, 10.0)], kind=CellKind.BLOCK),
    ]
    return RectangularGrid(rows=1, cols=2, cells=cells)


def test_document_round_trip(tmp_path: Path) -> None:
    image = _sample_image()
    grid = _sample_grid()
    annotations = [
        TextAnnotation(4.5, 5.0, "hello", None),
        TextAnnotation(10.5, 9.0, "world", (7, 8, 9)),
        LineAnnotation([(3.0, 2.0), (12.0, 4.0)], (1, 2, 3)),
        CurveAnnotation([(3.0, 2.0), (6.0, 6.0), (12.0, 5.0)], None),
    ]
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


def test_default_colour_omitted_on_disk(tmp_path: Path) -> None:
    """A default (None) colour is not written, keeping documents clean."""
    path = tmp_path / "doc.cwd"
    save_document(path, _sample_image(), [_sample_grid()], [TextAnnotation(3.0, 4.0, "hi", None)])

    payload = json.loads(path.read_text())
    assert payload["annotations"] == [{"type": "text", "x": 3.0, "y": 4.0, "text": "hi"}]

    assert load_document(path).annotations == [TextAnnotation(3.0, 4.0, "hi", None)]


def test_load_document_rejects_unknown_annotation_type(tmp_path: Path) -> None:
    path = tmp_path / "doc.cwd"
    save_document(path, _sample_image(), [_sample_grid()], [])
    payload = json.loads(path.read_text())
    payload["annotations"] = [{"type": "sparkle", "x": 3.0, "y": 4.0}]
    path.write_text(json.dumps(payload))
    with pytest.raises(DocumentError):
        load_document(path)


def test_load_document_rejects_wrong_format(tmp_path: Path) -> None:
    path = tmp_path / "bad.cwd"
    path.write_text('{"format": "something-else"}')
    with pytest.raises(DocumentError):
        load_document(path)


def test_load_document_rejects_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "doc.cwd"
    save_document(path, _sample_image(), [_sample_grid()], [])
    payload = json.loads(path.read_text())
    payload["version"] = 1
    path.write_text(json.dumps(payload))
    with pytest.raises(DocumentError):
        load_document(path)
