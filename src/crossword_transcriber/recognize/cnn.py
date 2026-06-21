"""EMNIST-trained CNN backend for single-letter recognition.

Inference uses ``cv2.dnn`` to load an ONNX model — no torch dependency.
The companion training script (``scripts/train_emnist.py``) requires the
optional ``[recognize]`` extra (torch + torchvision).
"""

from __future__ import annotations

import os

import cv2
import numpy as np

from . import Prediction

_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _softmax(x: np.ndarray) -> np.ndarray:
    e: np.ndarray = np.exp(x - x.max())
    return np.asarray(e / e.sum())


def preprocess_cell(gray: np.ndarray) -> np.ndarray:
    """Convert a grayscale cell crop to 28x28 EMNIST-compatible format.

    Finds the ink bounding box, fits it into a centred 20x20 region within a
    28x28 canvas, and inverts (EMNIST convention is white-on-black).  Returns
    ``uint8`` with values in ``[0, 255]``.
    """
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(binary)
    if coords is None:
        return np.zeros((28, 28), dtype=np.uint8)

    x, y, w, h = cv2.boundingRect(coords)
    ink = gray[y : y + h, x : x + w]

    scale = min(20.0 / max(w, 1), 20.0 / max(h, 1))
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = cv2.resize(ink, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.full((28, 28), 255, dtype=np.uint8)
    x_off = (28 - new_w) // 2
    y_off = (28 - new_h) // 2
    canvas[y_off : y_off + new_h, x_off : x_off + new_w] = resized

    return np.asarray(255 - canvas, dtype=np.uint8)


class CnnLetterClassifier:
    """Classify cell crops into uppercase A-Z using an ONNX model via ``cv2.dnn``."""

    def __init__(self, weights_path: str | os.PathLike[str]) -> None:
        self._net: cv2.dnn.Net = cv2.dnn.readNetFromONNX(os.fspath(weights_path))

    def predict(self, cell_image: np.ndarray) -> Prediction:
        gray = cell_image if cell_image.ndim == 2 else cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
        preprocessed = preprocess_cell(gray)
        blob = preprocessed.astype(np.float32).reshape(1, 1, 28, 28) / 255.0
        self._net.setInput(blob)
        output: np.ndarray = self._net.forward()
        probs = _softmax(output.flatten())
        idx = int(np.argmax(probs))
        return Prediction(letter=_LABELS[idx], confidence=float(probs[idx]))
