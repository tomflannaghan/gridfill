"""Phase 2 tests: rendering letters into an empty grid."""

from __future__ import annotations

import numpy as np
import pytest

from crossword_transcriber import write_grid

from .synthetic import make_grid


def _cell_ink_ratio(image: np.ndarray, x0: int, y0: int, cell: int) -> float:
    """Fraction of dark pixels in the central region of a cell (ignores borders)."""
    gray = image if image.ndim == 2 else image[:, :, 0]
    m = cell // 4  # inner-half crop to exclude grid lines
    region = gray[y0 + m : y0 + cell - m, x0 + m : x0 + cell - m]
    return float((region < 128).mean())


def test_write_places_ink_only_in_letter_cells() -> None:
    grid = make_grid(n_rows=3, n_cols=3, cell_px=80, with_clutter=False)
    letters = [["A", "", "B"], ["", "C", ""], ["D", "", "E"]]
    out = write_grid(grid.image, letters)

    x_origin, y_origin = grid.origin
    for r in range(3):
        for c in range(3):
            x0 = x_origin + c * grid.cell_px
            y0 = y_origin + r * grid.cell_px
            ratio = _cell_ink_ratio(out, x0, y0, grid.cell_px)
            if letters[r][c]:
                assert ratio > 0.04, f"expected ink at ({r},{c}), got {ratio:.3f}"
            else:
                assert ratio < 0.01, f"unexpected ink at ({r},{c}), got {ratio:.3f}"


def test_write_skips_block_cells() -> None:
    grid = make_grid(n_rows=2, n_cols=2, cell_px=80, with_clutter=False)
    out = write_grid(grid.image, [["A", None], [None, "B"]])
    x0, y0 = grid.origin
    # Block (None) cell at (0,1) stays blank.
    assert _cell_ink_ratio(out, x0 + grid.cell_px, y0, grid.cell_px) < 0.01


def test_write_rejects_shape_mismatch() -> None:
    grid = make_grid(n_rows=3, n_cols=3, cell_px=60, with_clutter=False)
    with pytest.raises(ValueError, match="does not match detected grid"):
        write_grid(grid.image, [["A", "B"], ["C", "D"]])


def test_write_saves_output_file(tmp_path) -> None:
    grid = make_grid(n_rows=2, n_cols=2, cell_px=60, with_clutter=False)
    out_file = tmp_path / "filled.png"
    write_grid(grid.image, [["A", "B"], ["C", "D"]], out_path=out_file)
    assert out_file.exists() and out_file.stat().st_size > 0


def test_write_under_rotation_composites_correctly() -> None:
    # Exercises the inverse-perspective warp-back: a rotated grid means a
    # non-trivial transform, so letters must be warped into the tilted frame.
    # Validate by un-rotating the output and checking ink lands in each cell
    # (re-running detection here would be confounded by the drawn glyphs
    # themselves surviving line extraction).
    import cv2

    grid = make_grid(n_rows=3, n_cols=3, cell_px=80, with_clutter=False)
    h, w = grid.image.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), 4.0, 1.0)
    inv_rot = cv2.getRotationMatrix2D((w / 2, h / 2), -4.0, 1.0)
    rotated = cv2.warpAffine(grid.image, rot, (w, h), borderValue=(255, 255, 255))

    letters = [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]
    out = write_grid(rotated, letters)
    unrotated = cv2.warpAffine(out, inv_rot, (w, h), borderValue=(255, 255, 255))

    x_origin, y_origin = grid.origin
    for r in range(3):
        for c in range(3):
            x0 = x_origin + c * grid.cell_px
            y0 = y_origin + r * grid.cell_px
            ratio = _cell_ink_ratio(unrotated, x0, y0, grid.cell_px)
            assert ratio > 0.04, f"expected ink at ({r},{c}), got {ratio:.3f}"


def test_write_preserves_grid_geometry() -> None:
    # Writing letters must not disturb the lattice: detection still finds 4x4.
    from crossword_transcriber.detection import detect_grid
    from crossword_transcriber.preprocess import binarize, to_grayscale
    from crossword_transcriber.segmentation import infer_cell_boxes

    grid = make_grid(n_rows=4, n_cols=4, cell_px=60, with_clutter=False)
    letters = [["X"] * 4 for _ in range(4)]
    out = write_grid(grid.image, letters)
    boxes = infer_cell_boxes(detect_grid(binarize(to_grayscale(out))).line_mask)
    assert len(boxes) == 4 and all(len(row) == 4 for row in boxes)
