"""Write pipeline: empty grid image + letters -> filled grid image."""

from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .detection import detect_grid
from .fonts import fit_font_size, font_loader
from .io import ImageSource, load_image, save_image
from .preprocess import binarize, to_grayscale
from .segmentation import infer_cell_boxes
from .types import CellKind, Grid, LetterGrid

_HIGHLIGHT_BGR = (50, 50, 255)
_BG_MARGIN_DIVISOR = 6


def write_grid(
    source: ImageSource,
    letters: Grid | LetterGrid,
    out_path: str | os.PathLike[str] | None = None,
    font_path: str | os.PathLike[str] | None = None,
    color: tuple[int, int, int] = (0, 0, 0),
    highlight_confidence: float | None = None,
) -> np.ndarray:
    """Render ``letters`` into the cells of an empty grid image.

    Detects and segments the grid, draws each letter centred and sized to fit its
    cell, composites onto a copy of the source, optionally saves to ``out_path``,
    and returns the resulting BGR image array.

    *letters* may be a plain :data:`LetterGrid` or a :class:`Grid` returned by
    :func:`read_grid`.  When a ``Grid`` is supplied its per-cell background
    colours are painted into the empty grid before the letters are drawn.

    If *highlight_confidence* is set, cells whose classifier confidence is below
    the threshold are filled with a bright red background instead of their
    original colour.

    ``None`` (block) and ``""`` (empty) cells are left untouched.
    """
    image = load_image(source).copy()
    detected = detect_grid(binarize(to_grayscale(image)))
    boxes = infer_cell_boxes(detected.line_mask)

    if isinstance(letters, Grid):
        grid = letters
        letter_grid = grid.to_letters()
    else:
        grid = None
        letter_grid = letters

    rows, cols = len(boxes), len(boxes[0])
    if len(letter_grid) != rows or any(len(r) != cols for r in letter_grid):
        given = f"{len(letter_grid)}x{len(letter_grid[0]) if letter_grid else 0}"
        raise ValueError(f"letters shape {given} does not match detected grid {rows}x{cols}")

    width, height = detected.size
    inverse = np.linalg.inv(detected.transform)
    src_h, src_w = image.shape[:2]

    # --- Background layer (only when a Grid with metadata is supplied) ---
    if grid is not None:
        bg_layer = np.zeros((height, width, 3), dtype=np.uint8)
        bg_mask = np.zeros((height, width), dtype=np.uint8)

        for row_boxes, row_cells in zip(boxes, grid.cells, strict=True):
            for box, cell in zip(row_boxes, row_cells, strict=True):
                if cell.kind is CellKind.BLOCK:
                    continue
                bg: tuple[int, int, int] | None = None
                if (
                    highlight_confidence is not None
                    and cell.confidence is not None
                    and cell.confidence < highlight_confidence
                ):
                    bg = _HIGHLIGHT_BGR
                elif cell.background is not None:
                    bg = cell.background
                if bg is None:
                    continue

                margin = max(2, min(box.width, box.height) // _BG_MARGIN_DIVISOR)
                x1 = box.x + margin
                y1 = box.y + margin
                x2 = box.x2 - margin
                y2 = box.y2 - margin
                bg_layer[y1:y2, x1:x2] = bg
                bg_mask[y1:y2, x1:x2] = 255

        if bg_mask.any():
            warped_bg = cv2.warpPerspective(bg_layer, inverse, (src_w, src_h))
            warped_mask = cv2.warpPerspective(bg_mask, inverse, (src_w, src_h))
            alpha = (warped_mask.astype(np.float32) / 255.0)[:, :, None]
            image = np.asarray(
                (image.astype(np.float32) * (1 - alpha) + warped_bg.astype(np.float32) * alpha)
                .round()
                .astype(np.uint8)
            )

    # --- Text layer ---
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    loader = font_loader(font_path)
    sample = boxes[0][0]
    font = loader(fit_font_size(loader, sample.width, sample.height))

    for row, letter_row in zip(boxes, letter_grid, strict=True):
        for box, letter in zip(row, letter_row, strict=True):
            if not letter:  # None (block) or "" (empty)
                continue
            cx = box.x + box.width / 2
            cy = box.y + box.height / 2
            draw.text((cx, cy), letter.upper(), font=font, fill=255, anchor="mm")

    warped = cv2.warpPerspective(np.array(mask), inverse, (src_w, src_h))
    alpha = (warped.astype(np.float32) / 255.0)[:, :, None]
    fill = np.array(color, dtype=np.float32).reshape(1, 1, 3)
    result = np.asarray(
        (image.astype(np.float32) * (1 - alpha) + fill * alpha).round().astype(np.uint8)
    )

    if out_path is not None:
        save_image(out_path, result)
    return result
