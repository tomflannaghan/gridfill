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
    foreground, which is what the morphology/segmentation stages expect.
    """
    raise NotImplementedError("Phase 1: implement adaptive binarization")
