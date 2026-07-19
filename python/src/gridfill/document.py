"""Save/load ``.cwd`` documents: the source image plus all grids, as JSON.

The rendered image is never stored -- a document carries exactly the
information needed to reconstruct it (the original image and the grid state),
so it can be reopened and edited further.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from .errors import DocumentError
from .types import Grid, Point, grid_from_dict

CWD_EXTENSION = ".cwd"

Colour = tuple[int, int, int]

# Annotations are free content drawn on top of the grid, a tagged union over
# *kinds* (text, line, curve). Each carries an optional BGR ``colour`` (``None``
# -> the editor's default black). Coordinates are source-image pixel positions,
# like cell polygons. Persisted as JSON objects, e.g.
# ``{"type": "text", "x": x, "y": y, "text": "..."}`` or
# ``{"type": "line", "points": [[x, y], [x, y]], "colour": [b, g, r]}``; ``colour``
# is omitted when ``None``. Mirrors web/src/annotations/types.ts.


@dataclass
class TextAnnotation:
    """Free text anchored at its top-left ``(x, y)``."""

    x: float
    y: float
    text: str
    colour: Colour | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "text",
            "x": self.x,
            "y": self.y,
            "text": self.text,
            **_colour_dict(self.colour),
        }


@dataclass
class LineAnnotation:
    """A straight line between two points."""

    points: list[Point]
    colour: Colour | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "line",
            "points": [list(p) for p in self.points],
            **_colour_dict(self.colour),
        }


@dataclass
class CurveAnnotation:
    """A smooth curve through its anchor points (>= 2)."""

    points: list[Point]
    colour: Colour | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "curve",
            "points": [list(p) for p in self.points],
            **_colour_dict(self.colour),
        }


Annotation = TextAnnotation | LineAnnotation | CurveAnnotation


def _colour_dict(colour: Colour | None) -> dict[str, Any]:
    """The ``colour`` key, present only when the colour is not the default."""
    return {} if colour is None else {"colour": list(colour)}


_FORMAT_MAGIC = "gridfill"
# Accepted on load so documents saved before the project's rename(s) still open.
_LEGACY_FORMAT_MAGICS = {"crossword-transcriber", "inkwell"}
# Bumped 1 -> 2 when coordinates switched from normalized [0, 1] fractions to
# source-image pixels; version-1 documents are not supported (no migration).
_FORMAT_VERSION = 2


@dataclass
class Document:
    """The full editable state of a session: source image, grids, annotations.

    Annotations are a tagged union (:class:`TextAnnotation`,
    :class:`LineAnnotation`, :class:`CurveAnnotation`) with coordinates as
    source-image pixel positions -- the same coordinate system as
    :class:`~gridfill.types.Cell` polygons -- and an optional BGR ``colour``
    (``None`` for the default black).
    """

    image: np.ndarray
    grids: list[Grid]
    annotations: list[Annotation] = field(default_factory=list)


def _document_payload(
    image: np.ndarray,
    grids: Sequence[Grid],
    annotations: Sequence[Annotation],
) -> dict[str, Any]:
    """Build the JSON-serializable ``.cwd`` payload for *image*, *grids*, *annotations*."""
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise OSError("Could not encode image for saving")

    return {
        "format": _FORMAT_MAGIC,
        "version": _FORMAT_VERSION,
        "image": {
            "encoding": "png",
            "data": base64.b64encode(encoded.tobytes()).decode("ascii"),
        },
        "grids": [grid.to_dict() for grid in grids],
        "annotations": [annotation.to_dict() for annotation in annotations],
    }


def document_to_json(
    image: np.ndarray,
    grids: Sequence[Grid],
    annotations: Sequence[Annotation],
) -> str:
    """Serialize *image*, *grids*, and *annotations* as a ``.cwd`` JSON string.

    Same document shape as :func:`save_document`, without writing to disk --
    for callers (e.g. the HTTP backend) that hand the document to a client
    directly rather than to the filesystem.
    """
    return json.dumps(_document_payload(image, grids, annotations))


def save_document(
    path: str | os.PathLike[str],
    image: np.ndarray,
    grids: Sequence[Grid],
    annotations: Sequence[Annotation],
) -> None:
    """Write *image*, *grids*, and *annotations* to *path* as a ``.cwd`` document."""
    payload = _document_payload(image, grids, annotations)
    with open(path, "w") as f:
        json.dump(payload, f)


def load_document(path: str | os.PathLike[str]) -> Document:
    """Load a ``.cwd`` document previously written by :func:`save_document`."""
    with open(path) as f:
        payload = json.load(f)

    if payload.get("format") not in {_FORMAT_MAGIC, *_LEGACY_FORMAT_MAGICS}:
        raise DocumentError(f"Not a gridfill document: {os.fspath(path)!r}")
    if payload.get("version") != _FORMAT_VERSION:
        # No migration path: versions before 2 stored normalized [0, 1]
        # coordinates rather than source-image pixels, so silently loading one
        # would misinterpret every coordinate rather than fail loudly.
        raise DocumentError(
            f"Unsupported document version {payload.get('version')!r} in "
            f"{os.fspath(path)!r} (expected {_FORMAT_VERSION})"
        )

    image_bytes = base64.b64decode(payload["image"]["data"])
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise DocumentError(f"Could not decode embedded image in {os.fspath(path)!r}")

    grids = [grid_from_dict(g) for g in payload["grids"]]
    annotations = [_annotation_from_json(a) for a in payload.get("annotations", [])]
    return Document(image=np.asarray(image), grids=grids, annotations=annotations)


def _annotation_from_json(o: dict[str, Any]) -> Annotation:
    """Parse one persisted annotation object into its :class:`Annotation`."""
    raw = o.get("colour")
    colour: Colour | None = (int(raw[0]), int(raw[1]), int(raw[2])) if raw is not None else None
    kind = o.get("type")
    if kind == "text":
        return TextAnnotation(float(o["x"]), float(o["y"]), str(o["text"]), colour)
    if kind == "line":
        return LineAnnotation(_parse_points(o["points"]), colour)
    if kind == "curve":
        return CurveAnnotation(_parse_points(o["points"]), colour)
    raise DocumentError(f"Unknown annotation type: {kind!r}")


def _parse_points(points: Sequence[Any]) -> list[Point]:
    return [(float(x), float(y)) for x, y in points]
