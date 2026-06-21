"""Helpers to synthesise crossword-grid images for tests.

Produces clean, programmatically-known grids so geometry tests don't depend on
real photos. Returns the image plus the ground-truth grid geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


@dataclass(frozen=True)
class SyntheticGrid:
    image: np.ndarray
    n_rows: int
    n_cols: int
    cell_px: int
    origin: tuple[int, int]  # (x, y) of the grid's top-left corner


def make_grid(
    n_rows: int = 5,
    n_cols: int = 5,
    cell_px: int = 60,
    pad: int = 50,
    line_thickness: int = 2,
    with_clutter: bool = True,
) -> SyntheticGrid:
    """Render an empty grid on a white page, optionally with non-grid clutter."""
    grid_w = n_cols * cell_px
    grid_h = n_rows * cell_px
    extra = 100 if with_clutter else 0
    canvas_w = grid_w + 2 * pad
    canvas_h = grid_h + 2 * pad + extra
    image = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

    x0, y0 = pad, pad
    for c in range(n_cols + 1):
        x = x0 + c * cell_px
        cv2.line(image, (x, y0), (x, y0 + grid_h), BLACK, line_thickness)
    for r in range(n_rows + 1):
        y = y0 + r * cell_px
        cv2.line(image, (x0, y), (x0 + grid_w, y), BLACK, line_thickness)

    if with_clutter:
        # Title above and a clue line below, to verify detection ignores them.
        cv2.putText(image, "PUZZLE", (x0, y0 - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, BLACK, 2)
        cv2.putText(
            image,
            "1 ACROSS some clue text",
            (x0, y0 + grid_h + 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            BLACK,
            2,
        )

    return SyntheticGrid(image, n_rows, n_cols, cell_px, (x0, y0))
