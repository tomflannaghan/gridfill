"""Polygon geometry helpers for measuring and placing content in Cell.polygon."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    # Only needed for annotations (stringized by ``from __future__ import
    # annotations``). Keeping it out of the runtime imports lets :mod:`types`
    # depend on this module for its pure-geometry helpers without a cycle.
    from .types import Point


def incircle(polygon_px: np.ndarray) -> tuple[float, float, int]:
    """Centre ``(x, y)`` and diameter, in pixels, of the polygon's incircle.

    The incircle is the largest circle that fits inside the polygon. Its
    diameter is a robust size metric for cells of any shape (square, rhombus,
    hexagon, curved wedge): unlike the axis-aligned bounding box, it reflects
    the room actually available for a glyph, ignoring thin spurs, points, and
    concave notches. Its centre is where a glyph sits most comfortably -- for an
    irregular cell that can be well away from the vertex centroid.

    Computed from a distance transform of the filled polygon: the peak distance
    is the inradius, and its location the centre. The centre is averaged over
    the peak region so an elongated cell (whose centres form a ridge, not a
    point) still resolves to the middle of that ridge.
    """
    x0 = int(np.floor(polygon_px[:, 0].min()))
    y0 = int(np.floor(polygon_px[:, 1].min()))
    x1 = int(np.ceil(polygon_px[:, 0].max()))
    y1 = int(np.ceil(polygon_px[:, 1].max()))
    w = max(1, x1 - x0)
    h = max(1, y1 - y0)
    # 1px zero border on every side so the distance transform measures distance
    # to the polygon's own edges; shift the polygon to match. The polygon spans
    # w+1 / h+1 columns/rows after the shift, so the mask needs a further +1 to
    # leave a zero border past the far edge (not just the near one).
    off_x, off_y = x0 - 1, y0 - 1
    mask = np.zeros((h + 3, w + 3), dtype=np.uint8)
    shifted = np.round(polygon_px - [off_x, off_y]).astype(np.int32)
    cv2.fillPoly(mask, [shifted], 255)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    radius = float(dist.max())
    ys, xs = np.where(dist >= radius - 0.5)
    cx = float(xs.mean()) + off_x
    cy = float(ys.mean()) + off_y
    return cx, cy, max(1, int(round(2 * radius)))


def polygon_centre(polygon: list[Point], resolution: int = 1024) -> Point:
    """The polygon's incircle centre, in the same normalized ``[0, 1]`` space.

    Preferred over the vertex mean for irregular cells: it returns the point
    deepest inside the polygon (where a glyph sits best and which navigation
    should treat as the cell's location), whereas a vertex mean drifts toward a
    cluster of vertices and can even fall outside a concave shape. Rasterizes
    the polygon at *resolution* pixels, takes its :func:`incircle` centre, and
    maps back to ``[0, 1]``.
    """
    polygon_px = np.asarray(polygon, dtype=np.float32) * resolution
    cx, cy, _ = incircle(polygon_px)
    return cx / resolution, cy / resolution


def convex_hull(points: list[Point]) -> list[Point]:
    """Counter-clockwise convex hull of *points* (Andrew's monotone chain).

    Pure Python (no cv2) so it works on normalized ``[0, 1]`` polygon vertices
    without going through a pixel array.
    """
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o: Point, a: Point, b: Point) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[Point] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Point] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]
