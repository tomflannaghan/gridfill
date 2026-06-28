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
from .types import LetterGrid


def write_grid(
    source: ImageSource,
    letters: LetterGrid,
    out_path: str | os.PathLike[str] | None = None,
    font_path: str | os.PathLike[str] | None = None,
    color: tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    """Render ``letters`` into the cells of an empty grid image.

    Detects and segments the grid, draws each letter centred and sized to fit its
    cell, composites onto a copy of the source, optionally saves to ``out_path``,
    and returns the resulting BGR image array.

    ``letters`` must match the detected grid shape. ``None`` (block) and ``""``
    (empty) cells are left untouched.
    """
    image = load_image(source).copy()
    detected = detect_grid(binarize(to_grayscale(image)))
    boxes = infer_cell_boxes(detected.line_mask)

    rows, cols = len(boxes), len(boxes[0])
    if len(letters) != rows or any(len(r) != cols for r in letters):
        given = f"{len(letters)}x{len(letters[0]) if letters else 0}"
        raise ValueError(f"letters shape {given} does not match detected grid {rows}x{cols}")

    # Draw text on an axis-aligned mask in the rectified frame, where every cell
    # is a clean rectangle.
    width, height = detected.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    loader = font_loader(font_path)
    sample = boxes[0][0]
    font = loader(fit_font_size(loader, sample.width, sample.height))

    for row, letter_row in zip(boxes, letters, strict=True):
        for box, letter in zip(row, letter_row, strict=True):
            if not letter:  # None (block) or "" (empty)
                continue
            cx = box.x + box.width / 2
            cy = box.y + box.height / 2
            draw.text((cx, cy), letter.upper(), font=font, fill=255, anchor="mm")

    # Warp the text mask from the rectified frame back into the source frame and
    # alpha-composite it onto the original image.
    inverse = np.linalg.inv(detected.transform)
    src_h, src_w = image.shape[:2]
    warped = cv2.warpPerspective(np.array(mask), inverse, (src_w, src_h))
    alpha = (warped.astype(np.float32) / 255.0)[:, :, None]
    fill = np.array(color, dtype=np.float32).reshape(1, 1, 3)
    result = np.asarray(
        (image.astype(np.float32) * (1 - alpha) + fill * alpha).round().astype(np.uint8)
    )

    if out_path is not None:
        save_image(out_path, result)
    return result
