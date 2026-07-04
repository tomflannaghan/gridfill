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


def quad_size(polygon_px: np.ndarray) -> tuple[int, int]:
    """Approximate (width, height) in pixels of a TL/TR/BR/BL quad."""
    top_left, top_right, bottom_right, bottom_left = polygon_px
    width = (np.linalg.norm(top_right - top_left) + np.linalg.norm(bottom_right - bottom_left)) / 2
    height = (np.linalg.norm(bottom_left - top_left) + np.linalg.norm(bottom_right - top_right)) / 2
    return max(1, int(round(float(width)))), max(1, int(round(float(height))))


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


def canvas_to_quad_homography(canvas_size: tuple[int, int], polygon_px: np.ndarray) -> np.ndarray:
    """Homography mapping a (canvas_w, canvas_h) raster's own corners onto *polygon_px*.

    ``polygon_px`` corners are in TL/TR/BR/BL order, matching the raster's own
    corners in the same order.
    """
    canvas_w, canvas_h = canvas_size
    canvas_corners = np.array(
        [[0, 0], [canvas_w, 0], [canvas_w, canvas_h], [0, canvas_h]], dtype=np.float32
    )
    dst = np.asarray(polygon_px, dtype=np.float32)
    return np.asarray(cv2.getPerspectiveTransform(canvas_corners, dst))
