"""EMNIST-trained CNN backend for single-letter recognition (Phase 4).

Implements the :class:`~crossword_transcriber.recognize.LetterClassifier`
protocol. Requires the optional ``recognize`` extra (torch/torchvision).
"""

from __future__ import annotations

import os

import numpy as np

from . import Prediction


class CnnLetterClassifier:
    """Classifies cell crops into uppercase A-Z with a small CNN."""

    def __init__(self, weights_path: str | os.PathLike[str]) -> None:
        self._weights_path = os.fspath(weights_path)
        raise NotImplementedError("Phase 4: load the trained CNN weights")

    def predict(self, cell_image: np.ndarray) -> Prediction:
        raise NotImplementedError("Phase 4: run inference and map to A-Z")
