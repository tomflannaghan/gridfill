"""Polygon geometry helpers for rendering/hit-testing against Cell.polygon."""

from __future__ import annotations

import cv2
import numpy as np

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
