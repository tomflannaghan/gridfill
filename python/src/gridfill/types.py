"""Core data types shared across grid detection and document I/O."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from .geometry import convex_hull, polygon_incircle

Point = tuple[float, float]


class CellKind(Enum):
    """What a grid cell contains.

    ``BLOCK`` only occurs in blocked (black-square) crosswords; barred grids use
    only ``EMPTY`` and ``LETTER``.
    """

    BLOCK = "block"
    EMPTY = "empty"
    LETTER = "letter"


@dataclass(frozen=True)
class BoundingBox:
    """An axis-aligned box in rectified-image pixel coordinates."""

    x: int
    y: int
    width: int
    height: int

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height


@dataclass
class Cell:
    """A single grid cell: its shape on the source image, kind, and content.

    ``polygon`` is the ordered list of the cell's vertices as (x, y) pixel
    coordinates of the *source* image -- i.e. the image originally passed to
    grid detection, not any internal rectified intermediate. For a rectangular
    cell this is always 4 points in
    ``[top-left, top-right, bottom-right, bottom-left]`` order. A cell carries
    no row/col of its own -- its position within a grid is purely a function
    of where it sits in the owning :class:`Grid`'s ``cells`` list.

    ``centre`` is the cell's incircle centre and ``size`` its incircle
    *diameter* (see :func:`gridfill.geometry.polygon_incircle`), both in the
    same source-image pixel space as ``polygon``. Both are derived from
    ``polygon`` and cached here so they are computed once and persisted to the
    document -- consumers (e.g. the web editor) read them directly instead of
    recomputing the distance transform. In particular, ``size`` is the basis
    for the web editor's letter font size, so a cell always renders its glyph
    at a consistent size without the frontend needing to know about incircles
    at all.

    ``text_colour`` is the BGR colour the cell's ``letter`` is drawn in; ``None``
    means the editor's default (black).
    """

    polygon: list[Point] = field(default_factory=list)
    kind: CellKind = CellKind.EMPTY
    letter: str | None = None
    background: tuple[int, int, int] | None = None
    centre: Point | None = None
    size: float | None = None
    text_colour: tuple[int, int, int] | None = None

    def __post_init__(self) -> None:
        # Derive centre and size together from the polygon's incircle (a
        # genuine cell has >= 3 vertices) -- one distance transform gives both.
        # An already-supplied value (e.g. from ``from_dict``) wins over the
        # freshly computed one, independently for each.
        if (self.centre is None or self.size is None) and len(self.polygon) >= 3:
            centre, size = polygon_incircle(self.polygon)
            if self.centre is None:
                self.centre = centre
            if self.size is None:
                self.size = size

    def to_dict(self) -> dict[str, Any]:
        return {
            "polygon": [list(p) for p in self.polygon],
            "kind": self.kind.value,
            "letter": self.letter,
            "background": list(self.background) if self.background is not None else None,
            "centre": list(self.centre) if self.centre is not None else None,
            "size": self.size,
            "text_colour": list(self.text_colour) if self.text_colour is not None else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Cell:
        bg = data["background"]
        centre = data.get("centre")
        size = data.get("size")
        tc = data.get("text_colour")
        return cls(
            polygon=[(float(x), float(y)) for x, y in data["polygon"]],
            kind=CellKind(data["kind"]),
            letter=data["letter"],
            background=(int(bg[0]), int(bg[1]), int(bg[2])) if bg is not None else None,
            centre=(float(centre[0]), float(centre[1])) if centre is not None else None,
            size=float(size) if size is not None else None,
            text_colour=(int(tc[0]), int(tc[1]), int(tc[2])) if tc is not None else None,
        )


class Grid(ABC):
    """Abstract base for any detected grid: an ordered list of cells.

    Concrete subclasses add geometry-specific metadata (e.g.
    :class:`RectangularGrid`'s row/column counts), but every ``Grid`` exposes a
    flat, ordered ``cells`` list so geometry-agnostic code can work with any
    grid shape without caring which subclass it has.
    """

    cells: list[Cell]

    @abstractmethod
    def bounding_polygon(self) -> list[Point]:
        """The grid's own outer boundary, in the same source-image pixel
        space as :attr:`Cell.polygon`."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict, including a ``"type"`` key
        identifying the concrete subclass (see :func:`register_grid_type` and
        :func:`grid_from_dict`)."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> Grid:
        """Deserialize a dict produced by :meth:`to_dict`."""


_GRID_TYPES: dict[str, type[Grid]] = {}

_GridT = TypeVar("_GridT", bound=type[Grid])


def register_grid_type(type_name: str) -> Callable[[_GridT], _GridT]:
    """Class decorator registering a :class:`Grid` subclass under *type_name*
    so :func:`grid_from_dict` can dispatch to it when loading a saved document."""

    def decorator(grid_cls: _GridT) -> _GridT:
        _GRID_TYPES[type_name] = grid_cls
        return grid_cls

    return decorator


def grid_from_dict(data: dict[str, Any]) -> Grid:
    """Deserialize a dict produced by any registered ``Grid.to_dict()``."""
    type_name = data["type"]
    grid_cls = _GRID_TYPES.get(type_name)
    if grid_cls is None:
        raise ValueError(f"Unknown grid type: {type_name!r}")
    return grid_cls.from_dict(data)


@register_grid_type("rectangular")
@dataclass
class RectangularGrid(Grid):
    """A grid laid out on a regular row/column lattice.

    ``cells`` is stored in row-major (reading) order; use :meth:`cell` to
    address a specific row and column.
    """

    rows: int
    cols: int
    cells: list[Cell]

    def cell(self, row: int, col: int) -> Cell:
        return self.cells[row * self.cols + col]

    def bounding_polygon(self) -> list[Point]:
        top_left = self.cell(0, 0).polygon[0]
        top_right = self.cell(0, self.cols - 1).polygon[1]
        bottom_right = self.cell(self.rows - 1, self.cols - 1).polygon[2]
        bottom_left = self.cell(self.rows - 1, 0).polygon[3]
        return [top_left, top_right, bottom_right, bottom_left]

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "rectangular",
            "rows": self.rows,
            "cols": self.cols,
            "cells": [cell.to_dict() for cell in self.cells],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RectangularGrid:
        return cls(
            rows=data["rows"],
            cols=data["cols"],
            cells=[Cell.from_dict(c) for c in data["cells"]],
        )


@register_grid_type("irregular")
@dataclass
class IrregularGrid(Grid):
    """A grid of arbitrarily-shaped cells forming a continuous lattice.

    Unlike :class:`RectangularGrid` there is no row/column structure: cells can
    be rhombi, hexagons, curved wedges, etc. ``cells`` is a flat list ordered
    top-to-bottom then left-to-right by centroid. Each :class:`Cell` carries its
    own polygon, so the geometry lives entirely in the cells.
    """

    cells: list[Cell]

    def bounding_polygon(self) -> list[Point]:
        return convex_hull([pt for cell in self.cells for pt in cell.polygon])

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "irregular",
            "cells": [cell.to_dict() for cell in self.cells],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IrregularGrid:
        return cls(cells=[Cell.from_dict(c) for c in data["cells"]])
