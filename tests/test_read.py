"""Phase 5 tests: end-to-end read pipeline and round-trip tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from crossword_transcriber import read_grid, write_grid
from crossword_transcriber.recognize import LetterClassifier, Prediction

from .synthetic import make_grid

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockClassifier:
    """Returns a fixed letter for every cell, tracking call count."""

    def __init__(self, letter: str = "X") -> None:
        self.letter = letter
        self.call_count = 0

    def predict(self, cell_image: np.ndarray) -> Prediction:
        self.call_count += 1
        return Prediction(letter=self.letter, confidence=0.99)


class SequenceClassifier:
    """Returns successive letters from a pre-set sequence."""

    def __init__(self, letters: str) -> None:
        self._letters = letters
        self._idx = 0

    def predict(self, cell_image: np.ndarray) -> Prediction:
        letter = self._letters[self._idx]
        self._idx += 1
        return Prediction(letter=letter, confidence=0.99)


# ---------------------------------------------------------------------------
# Round-trip: write then read
# ---------------------------------------------------------------------------


def test_round_trip_all_letters() -> None:
    """Write letters into every cell, read them back with a mock classifier.

    Large padding ensures the morphological kernel is longer than any
    machine-rendered letter stroke (the kernel is image_width // 20).
    """
    grid = make_grid(n_rows=3, n_cols=3, cell_px=60, pad=400, with_clutter=False)
    letters = [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]
    written = write_grid(grid.image, letters)

    seq = "ABCDEFGHI"
    clf = SequenceClassifier(seq)
    result = read_grid(written, classifier=clf)

    assert len(result) == 3
    assert all(len(row) == 3 for row in result)
    flat = [c for row in result for c in row]
    assert flat == list(seq)
    assert clf._idx == 9


def test_round_trip_with_empties() -> None:
    """Empty cells should stay empty; only letter cells reach the classifier."""
    grid = make_grid(n_rows=2, n_cols=2, cell_px=60, pad=400, with_clutter=False)
    letters = [["A", ""], ["", "B"]]
    written = write_grid(grid.image, letters)

    clf = MockClassifier("X")
    result = read_grid(written, classifier=clf)

    assert result[0][0] == "X"
    assert result[0][1] == ""
    assert result[1][0] == ""
    assert result[1][1] == "X"
    assert clf.call_count == 2


# ---------------------------------------------------------------------------
# Without a classifier
# ---------------------------------------------------------------------------


def test_read_without_classifier() -> None:
    """Without a classifier, letter cells should return '' rather than crash."""
    grid = make_grid(n_rows=2, n_cols=2, cell_px=60, pad=400, with_clutter=False)
    written = write_grid(grid.image, [["A", "B"], ["C", "D"]])

    result = read_grid(written)
    assert len(result) == 2
    assert all(len(row) == 2 for row in result)
    assert all(c == "" for row in result for c in row)


# ---------------------------------------------------------------------------
# Fixture integration
# ---------------------------------------------------------------------------


def test_read_fixture_dimensions() -> None:
    """read_grid on a real fixture should produce the correct grid shape."""
    result = read_grid(str(FIXTURES / "barred.png"))
    assert len(result) == 12
    assert all(len(row) == 12 for row in result)
    assert all(c is not None for row in result for c in row)


def test_read_barred_fixture_all_letter() -> None:
    """Every cell in the fully-filled barred fixture should reach the classifier."""
    clf = MockClassifier("X")
    result = read_grid(str(FIXTURES / "barred.png"), classifier=clf)

    assert len(result) == 12
    assert all(len(row) == 12 for row in result)
    assert clf.call_count == 144
    assert all(c == "X" for row in result for c in row)


def test_mock_classifiers_satisfy_protocol() -> None:
    assert isinstance(MockClassifier(), LetterClassifier)
    assert isinstance(SequenceClassifier("A"), LetterClassifier)
