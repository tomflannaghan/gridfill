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


@dataclass(frozen=True)
class SyntheticBrickGrid:
    image: np.ndarray
    n_cells: int


def make_brick_grid(
    n_rows: int = 6,
    n_cols: int = 6,
    cell_w: int = 60,
    cell_h: int = 40,
    pad: int = 50,
    line_thickness: int = 2,
) -> SyntheticBrickGrid:
    """Render a running-bond brick wall on a white page.

    Alternate rows are offset by half a cell width, with half-width bricks at
    the row ends (like a real brick-pattern crossword grid). Cells are
    rectangles, but no vertical line runs continuously across more than one
    row, so this can't be found by rectangular (line-lattice) detection --
    it's a minimal case for exercising irregular detection's adjacency step.
    """
    grid_w = n_cols * cell_w
    grid_h = n_rows * cell_h
    canvas_w = grid_w + 2 * pad
    canvas_h = grid_h + 2 * pad
    image = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)
    x0, y0 = pad, pad

    cv2.rectangle(image, (x0, y0), (x0 + grid_w, y0 + grid_h), BLACK, line_thickness)
    for r in range(1, n_rows):
        y = y0 + r * cell_h
        cv2.line(image, (x0, y), (x0 + grid_w, y), BLACK, line_thickness)

    half = cell_w // 2
    n_cells = 0
    for r in range(n_rows):
        y_top = y0 + r * cell_h
        y_bot = y0 + (r + 1) * cell_h
        offset = half if r % 2 == 1 else 0
        dividers = [x for x in range(x0 + offset, x0 + grid_w, cell_w) if x0 < x < x0 + grid_w]
        for x in dividers:
            cv2.line(image, (x, y_top), (x, y_bot), BLACK, line_thickness)
        n_cells += len(dividers) + 1

    return SyntheticBrickGrid(image, n_cells)
