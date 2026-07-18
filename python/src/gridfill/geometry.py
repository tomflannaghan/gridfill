"""Polygon geometry helpers for rendering/hit-testing against Cell.polygon."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    # Only needed for annotations (stringized by ``from __future__ import
    # annotations``). Keeping it out of the runtime imports lets :mod:`types`
    # depend on this module for its pure-geometry helpers without a cycle.
    from .types import Point


def polygon_to_pixels(polygon: list[Point], image_size: tuple[int, int]) -> np.ndarray:
    """Convert a normalized [0, 1] polygon to an (N, 2) float32 pixel array."""
    w, h = image_size
    return np.array([(x * w, y * h) for x, y in polygon], dtype=np.float32)


def point_in_polygon(x: float, y: float, polygon_px: np.ndarray) -> bool:
    return cv2.pointPolygonTest(polygon_px, (float(x), float(y)), False) >= 0


def incircle(polygon_px: np.ndarray) -> tuple[float, float, int]:
    """Center ``(x, y)`` and diameter, in pixels, of the polygon's incircle.

    The incircle is the largest circle that fits inside the polygon. Its
    diameter is a robust size metric for cells of any shape (square, rhombus,
    hexagon, curved wedge): unlike the axis-aligned bounding box, it reflects
    the room actually available for a glyph, ignoring thin spurs, points, and
    concave notches. Its center is where a glyph sits most comfortably -- for an
    irregular cell that can be well away from the vertex centroid.

    Computed from a distance transform of the filled polygon: the peak distance
    is the inradius, and its location the center. The center is averaged over
    the peak region so an elongated cell (whose centers form a ridge, not a
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


def inset_quad(polygon_px: np.ndarray, frac: float) -> np.ndarray:
    """Shrink a quad toward its own centroid by *frac* (0-1).

    Keeps a background fill from bleeding onto the grid lines bordering a cell.
    """
    centroid = polygon_px.mean(axis=0)
    return np.asarray(centroid + (polygon_px - centroid) * (1 - frac))


def bounding_rect(
    polygon_px: np.ndarray, image_size: tuple[int, int], margin: int = 0
) -> tuple[int, int, int, int]:
    """Integer (x0, y0, x1, y1) bounding rect, clipped to the image bounds."""
    w, h = image_size
    x0 = max(int(np.floor(polygon_px[:, 0].min())) - margin, 0)
    y0 = max(int(np.floor(polygon_px[:, 1].min())) - margin, 0)
    x1 = min(int(np.ceil(polygon_px[:, 0].max())) + margin, w)
    y1 = min(int(np.ceil(polygon_px[:, 1].max())) + margin, h)
    return x0, y0, x1, y1


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


def polygon_centroid(polygon: list[Point]) -> Point:
    """Mean of a polygon's vertices -- a cheap, good-enough cell centre."""
    n = len(polygon)
    return sum(x for x, _ in polygon) / n, sum(y for _, y in polygon) / n
