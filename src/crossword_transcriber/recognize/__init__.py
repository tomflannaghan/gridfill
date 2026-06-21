"""Handwritten letter recognition backends.

The pipeline depends only on the :class:`LetterClassifier` protocol, so backends
(EMNIST CNN, local TrOCR, ...) can be swapped without touching the rest of the
code. All backends classify a single cropped cell into one uppercase letter A-Z.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class Prediction:
    """A predicted letter and the model's confidence in ``[0, 1]``."""

    letter: str
    confidence: float


@runtime_checkable
class LetterClassifier(Protocol):
    """Classifies a single cropped, preprocessed cell image into a letter.

    Implementations must constrain the output to uppercase ``A``-``Z``.
    """

    def predict(self, cell_image: np.ndarray) -> Prediction:
        """Classify one cell crop (grayscale, letter ink on a light background)."""
        ...
