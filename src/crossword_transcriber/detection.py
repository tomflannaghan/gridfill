"""Grid detection and perspective rectification.

Detection is driven purely off the line lattice, which is present in both blocked
and barred grids -- we never rely on black blocks existing.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .errors import GridDetectionError


@dataclass
class DetectedGrid:
    """The rectified grid lattice plus the transform that produced it."""

    # Rectified, axis-aligned binary line mask containing just the grid lattice.
    line_mask: np.ndarray
    # 3x3 perspective transform from source -> rectified coords.
    transform: np.ndarray
    # (width, height) of the rectified space, for warping other source layers.
    size: tuple[int, int]


def extract_line_mask(binary: np.ndarray) -> np.ndarray:
    """Isolate the long horizontal and vertical strokes (grid lines).

    Morphological opening with long 1-D kernels keeps only runs longer than the
    kernel, which removes letters and clue numbers while preserving grid lines.
    """
    height, width = binary.shape[:2]
    h_size = max(10, width // 20)
    v_size = max(10, height // 20)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_size, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    return cv2.bitwise_or(horizontal, vertical)


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Order four points as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    coord_sum = pts.sum(axis=1)
    coord_diff = np.diff(pts, axis=1).ravel()
    rect[0] = pts[np.argmin(coord_sum)]  # top-left: smallest x + y
    rect[2] = pts[np.argmax(coord_sum)]  # bottom-right: largest x + y
    rect[1] = pts[np.argmin(coord_diff)]  # top-right: smallest y - x
    rect[3] = pts[np.argmax(coord_diff)]  # bottom-left: largest y - x
    return rect


def _grid_quad(line_mask: np.ndarray) -> np.ndarray:
    """Find the four corners of the grid lattice's outer boundary."""
    contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise GridDetectionError("No line structure found in image")

    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) <= 0:
        raise GridDetectionError("Largest line contour has no area")

    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
    if len(approx) == 4:
        quad = approx.reshape(4, 2).astype(np.float32)
    else:
        # Fall back to the minimum-area rectangle when the contour is not a clean
        # quadrilateral (e.g. rounded or noisy corners).
        quad = cv2.boxPoints(cv2.minAreaRect(contour)).astype(np.float32)
    return _order_corners(quad)


def detect_grid(binary: np.ndarray) -> DetectedGrid:
    """Locate the crossword lattice on the page and rectify it.

    Extracts the line lattice, finds its outer quad, and warps it to an
    axis-aligned crop. The returned transform/size let callers warp other layers
    (e.g. the grayscale image) into the same rectified frame.
    """
    line_mask = extract_line_mask(binary)
    quad = _grid_quad(line_mask)
    top_left, top_right, bottom_right, bottom_left = quad

    width = int(
        round(
            max(
                np.linalg.norm(top_right - top_left),
                np.linalg.norm(bottom_right - bottom_left),
            )
        )
    )
    height = int(
        round(
            max(
                np.linalg.norm(bottom_left - top_left),
                np.linalg.norm(bottom_right - top_right),
            )
        )
    )
    if width < 2 or height < 2:
        raise GridDetectionError(f"Degenerate grid size: {width}x{height}")

    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(quad, dst)
    rectified = cv2.warpPerspective(line_mask, transform, (width, height))
    return DetectedGrid(line_mask=rectified, transform=transform, size=(width, height))
