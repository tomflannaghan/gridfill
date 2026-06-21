"""Image preprocessing for grid detection (grayscale, threshold, denoise).

v1 targets clean scans, so this stays deliberately light. Heavier illumination
correction can be layered in here later for phone-photo support.
"""

from __future__ import annotations

import cv2
import numpy as np


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert a BGR image to single-channel grayscale."""
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def binarize(gray: np.ndarray) -> np.ndarray:
    """Adaptive threshold to a binary image (ink = 255, background = 0).

    Returns an inverted binary image so that grid lines and letters are the
    foreground, which is what the morphology/segmentation stages expect. Adaptive
    (rather than global) thresholding tolerates the mild brightness gradients
    found even in clean scans.
    """
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    # Block size scales with image size but stays odd and not too small.
    block_size = max(15, (min(gray.shape[:2]) // 40) | 1)
    if block_size % 2 == 0:
        block_size += 1
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size,
        10,
    )
