"""Write pipeline: empty grid image + letters -> filled grid image."""

from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .detection import detect_grid
from .fonts import _best_grid, fit_font_size, fit_font_size_multi, font_loader
from .io import ImageSource, load_image, save_image
from .preprocess import binarize, to_grayscale
from .segmentation import infer_cell_boxes
from .types import CellKind, Grid, LetterGrid

_HIGHLIGHT_BGR = (50, 50, 255)
_WHITE_DISTANCE_THRESHOLD = 30


def write_grid(
    source: ImageSource,
    letters: Grid | LetterGrid,
    out_path: str | os.PathLike[str] | None = None,
    font_path: str | os.PathLike[str] | None = None,
    color: tuple[int, int, int] = (0, 0, 0),
    highlight_confidence: float | None = None,
    grid_index: int | None = None,
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
    detected = detect_grid(binarize(to_grayscale(image)), grid_index=grid_index)
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
        line_mask_bool = detected.line_mask > 0
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
                if bg != _HIGHLIGHT_BGR:
                    dist = sum((a - 255) ** 2 for a in bg)
                    if dist < _WHITE_DISTANCE_THRESHOLD**2:
                        continue

                bg_layer[box.y : box.y2, box.x : box.x2] = bg
                bg_mask[box.y : box.y2, box.x : box.x2] = 255

        bg_mask[line_mask_bool] = 0

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
    single_font = loader(fit_font_size(loader, sample.width, sample.height))

    multi_font_cache: dict[tuple[int, int], ImageFont.FreeTypeFont] = {}

    for lr in letter_grid:
        for lv in lr:
            if lv and len(lv) > 1:
                gr = _best_grid(len(lv), sample.width, sample.height)
                if gr not in multi_font_cache:
                    sz = fit_font_size_multi(loader, sample.width, sample.height, gr[0], gr[1])
                    multi_font_cache[gr] = loader(sz)

    for row, letter_row in zip(boxes, letter_grid, strict=True):
        for box, letter in zip(row, letter_row, strict=True):
            if not letter:  # None (block) or "" (empty)
                continue
            text = letter.upper()
            if len(text) == 1:
                cx = box.x + box.width / 2
                cy = box.y + box.height / 2
                draw.text((cx, cy), text, font=single_font, fill=255, anchor="mm")
            else:
                nrows, ncols = _best_grid(len(text), box.width, box.height)
                font = multi_font_cache[(nrows, ncols)]
                slot_w = box.width / ncols
                slot_h = box.height / nrows
                for i, ch in enumerate(text):
                    r = i // ncols
                    c = i % ncols
                    cx = box.x + (c + 0.5) * slot_w
                    cy = box.y + (r + 0.5) * slot_h
                    draw.text((cx, cy), ch, font=font, fill=255, anchor="mm")

    warped = cv2.warpPerspective(np.array(mask), inverse, (src_w, src_h))
    alpha = (warped.astype(np.float32) / 255.0)[:, :, None]
    fill = np.array(color, dtype=np.float32).reshape(1, 1, 3)
    result = np.asarray(
        (image.astype(np.float32) * (1 - alpha) + fill * alpha).round().astype(np.uint8)
    )

    if out_path is not None:
        save_image(out_path, result)
    return result
