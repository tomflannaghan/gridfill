"""Phase 4 tests: letter recognition (preprocessing + inference)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from crossword_transcriber.recognize import LetterClassifier, Prediction
from crossword_transcriber.recognize.cnn import CnnLetterClassifier, _softmax, preprocess_cell

# ---------------------------------------------------------------------------
# preprocess_cell
# ---------------------------------------------------------------------------


class TestPreprocessCell:
    def test_output_shape(self) -> None:
        cell = np.full((50, 40), 230, dtype=np.uint8)
        cell[15:35, 10:30] = 20
        result = preprocess_cell(cell)
        assert result.shape == (28, 28)
        assert result.dtype == np.uint8

    def test_empty_cell_returns_zeros(self) -> None:
        cell = np.full((40, 40), 240, dtype=np.uint8)
        result = preprocess_cell(cell)
        assert result.shape == (28, 28)
        assert result.sum() == 0

    def test_ink_is_inverted(self) -> None:
        """Dark-on-light input should produce white-on-black output."""
        cell = np.full((40, 40), 240, dtype=np.uint8)
        cell[10:30, 10:30] = 20  # dark ink
        result = preprocess_cell(cell)
        assert result[14, 14] > 128, "ink region should be bright after inversion"

    def test_ink_is_centred(self) -> None:
        """Ink placed off-centre should end up near the middle of the 28x28 output."""
        cell = np.full((60, 60), 240, dtype=np.uint8)
        cell[40:50, 40:50] = 20  # bottom-right ink
        result = preprocess_cell(cell)
        # The bright (ink) mass should be centred
        ys, xs = np.where(result > 50)
        assert abs(ys.mean() - 14) < 5, "ink should be vertically centred"
        assert abs(xs.mean() - 14) < 5, "ink should be horizontally centred"

    def test_aspect_ratio_preserved(self) -> None:
        """A tall, narrow letter should stay tall and narrow, not get squashed."""
        cell = np.full((60, 60), 240, dtype=np.uint8)
        cell[5:55, 25:35] = 20  # tall narrow stroke
        result = preprocess_cell(cell)
        ys, xs = np.where(result > 50)
        h_span = ys.max() - ys.min()
        w_span = xs.max() - xs.min()
        assert h_span > w_span * 2, "tall stroke should remain taller than wide"


# ---------------------------------------------------------------------------
# _softmax
# ---------------------------------------------------------------------------


class TestSoftmax:
    def test_uniform_input(self) -> None:
        x = np.zeros(26, dtype=np.float32)
        probs = _softmax(x)
        np.testing.assert_allclose(probs, 1.0 / 26, atol=1e-6)

    def test_peaked_input(self) -> None:
        x = np.zeros(26, dtype=np.float32)
        x[0] = 100.0
        probs = _softmax(x)
        assert probs[0] > 0.99
        assert probs.sum() == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# CnnLetterClassifier (mocked inference)
# ---------------------------------------------------------------------------


def _make_classifier() -> CnnLetterClassifier:
    """Build a CnnLetterClassifier with a mocked ONNX network."""
    mock_net = MagicMock()
    with patch.object(cv2.dnn, "readNetFromONNX", return_value=mock_net):
        return CnnLetterClassifier("dummy.onnx")


class TestCnnLetterClassifier:
    def test_satisfies_protocol(self) -> None:
        cls = _make_classifier()
        assert isinstance(cls, LetterClassifier)

    def test_predict_returns_correct_letter(self) -> None:
        cls = _make_classifier()
        logits = np.full(26, -10.0, dtype=np.float32)
        logits[2] = 10.0  # class 2 → 'C'
        cls._net.forward.return_value = logits.reshape(1, 26)

        cell = np.full((40, 40), 240, dtype=np.uint8)
        cell[10:30, 10:30] = 30
        result = cls.predict(cell)

        assert result.letter == "C"
        assert result.confidence > 0.9

    def test_predict_handles_bgr(self) -> None:
        cls = _make_classifier()
        logits = np.zeros(26, dtype=np.float32)
        logits[25] = 10.0  # class 25 → 'Z'
        cls._net.forward.return_value = logits.reshape(1, 26)

        cell = np.full((40, 40, 3), 240, dtype=np.uint8)
        cell[10:30, 10:30] = 30
        result = cls.predict(cell)
        assert result.letter == "Z"

    def test_prediction_dataclass(self) -> None:
        p = Prediction(letter="A", confidence=0.95)
        assert p.letter == "A"
        assert p.confidence == 0.95
