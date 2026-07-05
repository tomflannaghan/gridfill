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


def polygon_size(polygon_px: np.ndarray) -> tuple[int, int]:
    """Approximate (width, height) in pixels of a polygon, from its extent.

    Uses the axis-aligned bounding box so it works for a cell of any shape
    (square, rhombus, hexagon, curved wedge), not just a 4-corner quad.
    """
    xs, ys = polygon_px[:, 0], polygon_px[:, 1]
    width = float(xs.max() - xs.min())
    height = float(ys.max() - ys.min())
    return max(1, int(round(width))), max(1, int(round(height)))


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
