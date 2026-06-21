"""Read pipeline: scan image -> 2D array of letters."""

from __future__ import annotations

from .io import ImageSource
from .recognize import LetterClassifier
from .types import LetterGrid


def read_grid(
    source: ImageSource,
    classifier: LetterClassifier | None = None,
) -> LetterGrid:
    """Transcribe a filled crossword scan into a list-of-lists of letters.

    ``None`` marks a block cell, ``""`` an empty white cell, and ``"A".."Z"`` a
    recognised letter. Pass a ``classifier`` to override the default HCR backend.
    """
    raise NotImplementedError("Phase 5: wire up the full read pipeline")
