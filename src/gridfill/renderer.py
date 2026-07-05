"""Composite a grid overlay onto its background image.

Pure BGR image composition with no Tk dependency: given a base image, the grids
with their fitted fonts, and the current selection/annotation state, produce the
frame the editor shows on screen or writes to disk. Keeping this Tk-free makes it
unit-testable without a display.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .fonts import FontT, fit_multiline
from .geometry import bounding_rect, incircle, inset_quad, polygon_to_pixels
from .types import Cell, CellKind, Grid

_SELECTION_BGR = (255, 180, 0)
_ACTIVE_GRID_BGR = (0, 180, 0)
_WHITE_DISTANCE_THRESHOLD = 30
_CELL_FILL_INSET_FRAC = 0.06
_BLANK_ICON_SIZE_FRAC = 0.4  # fraction of the shorter side the blank-state icon spans
_MULTI_TEXT_FILL = 0.85  # fraction of cell height a multi-line letter stack may span


@dataclass(frozen=True)
class GridLayer:
    """One grid to render, with the font set chosen for the target resolution.

    The editor keeps separate display- and export-resolution fonts per grid (see
    :class:`~gridfill.editor._GridState`); it picks one set per render and packs
    it into a layer so the renderer stays oblivious to that optimization.
    ``multi_font_cache`` is passed by reference so glyph fonts fitted while
    rendering persist back to the owning grid state.
    """

    grid: Grid
    single_font: FontT
    ref_cell_size: int
    multi_font_cache: dict[str, tuple[list[str], FontT]]


def _cell_highlight_color(cell: Cell) -> tuple[int, int, int] | None:
    """The cell's background fill colour, or ``None`` if unset or near-white."""
    bg = cell.background
    if bg is None:
        return None
    dist = sum((a - 255) ** 2 for a in bg)
    if dist < _WHITE_DISTANCE_THRESHOLD**2:
        return None
    return bg


class GridRenderer:
    """Renders grid overlays (letters, highlights, selection, annotations)."""

    def __init__(
        self,
        color: tuple[int, int, int],
        loader: Callable[[int], FontT],
        icon_bgra: np.ndarray,
    ) -> None:
        self._color = color
        self._loader = loader
        self._icon_bgra = icon_bgra

    def compute_base_image(self, image: np.ndarray, grids: list[Grid]) -> np.ndarray:
        """The background image with every highlighted cell's colour filled in.

        This is the expensive-but-static layer; the editor caches it and only
        recomputes it when a highlight changes or the display size does.
        """
        src_h, src_w = image.shape[:2]
        result = image.astype(np.float32).copy()

        for grid in grids:
            for cell in grid.cells:
                if cell.kind is CellKind.BLOCK:
                    continue
                bg = _cell_highlight_color(cell)
                if bg is None:
                    continue
                polygon_px = polygon_to_pixels(cell.polygon, (src_w, src_h))
                inset_px = inset_quad(polygon_px, _CELL_FILL_INSET_FRAC)
                x0, y0, x1, y1 = bounding_rect(inset_px, (src_w, src_h))
                if x1 <= x0 or y1 <= y0:
                    continue
                mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
                cv2.fillConvexPoly(mask, (inset_px - [x0, y0]).astype(np.int32), 255)
                alpha = (mask.astype(np.float32) / 255.0)[:, :, None]
                fill = np.array(bg, dtype=np.float32).reshape(1, 1, 3)
                result[y0:y1, x0:x1] = result[y0:y1, x0:x1] * (1 - alpha) + fill * alpha

        return np.asarray(np.clip(result, 0, 255).round().astype(np.uint8))

    def render(
        self,
        base: np.ndarray,
        image_size: tuple[int, int],
        layers: list[GridLayer],
        *,
        annotations: list[tuple[float, float, str]],
        annotation_font: FontT | None,
        draw_blank_icon: bool = False,
        active_grid_index: int | None = None,
        selected: int | None = None,
        multi_entry: bool = False,
    ) -> np.ndarray:
        """Composite the full frame onto a copy of *base*.

        The overlay arguments (icon, active-grid indicator, selection) are the
        interactive-only chrome; an export render passes them off so it produces
        just the letters, highlights, and annotations.
        """
        result = base.copy()

        if draw_blank_icon:
            result = self._draw_centered_icon(result)

        for layer in layers:
            for cell in layer.grid.cells:
                if cell.kind is CellKind.LETTER and cell.letter:
                    self._draw_letter_in_cell(
                        result,
                        cell,
                        image_size,
                        layer.single_font,
                        layer.ref_cell_size,
                        layer.multi_font_cache,
                    )

        # Active grid indicator (only meaningful when there's more than one grid).
        if active_grid_index is not None and len(layers) > 1:
            grid = layers[active_grid_index].grid
            hull_px = polygon_to_pixels(grid.bounding_polygon(), image_size).astype(np.int32)
            cv2.polylines(result, [hull_px], True, _ACTIVE_GRID_BGR, 2)

        # Cell selection highlight.
        if selected is not None and active_grid_index is not None:
            cell = layers[active_grid_index].grid.cells[selected]
            poly_px = polygon_to_pixels(cell.polygon, image_size).astype(np.int32)
            thickness = 3 if multi_entry else 2
            cv2.polylines(result, [poly_px], True, _SELECTION_BGR, thickness)

        # Text annotations -- stored in normalized [0, 1] source coordinates (like
        # cell polygons), so scale them to the current image space.
        if annotations and annotation_font is not None:
            img_w, img_h = image_size
            pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            b, g, r = self._color
            rgb_color = (r, g, b)
            for ax, ay, text in annotations:
                draw.text(
                    (ax * img_w, ay * img_h),
                    text,
                    font=annotation_font,
                    fill=rgb_color,
                    anchor="ls",
                )
            result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        return result

    def _draw_letter_in_cell(
        self,
        result: np.ndarray,
        cell: Cell,
        image_size: tuple[int, int],
        single_font: FontT,
        ref_cell_size: int,
        multi_font_cache: dict[str, tuple[list[str], FontT]],
    ) -> None:
        text = (cell.letter or "").upper()
        if not text:
            return
        polygon_px = polygon_to_pixels(cell.polygon, image_size)
        cx, cy, diameter = incircle(polygon_px)
        cell_h = diameter

        x0, y0, x1, y1 = bounding_rect(polygon_px, image_size, margin=1)
        if x1 <= x0 or y1 <= y0:
            return
        local_cx, local_cy = cx - x0, cy - y0

        pil_img = Image.fromarray(cv2.cvtColor(result[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        b, g, r = self._color
        rgb_color = (r, g, b)

        if len(text) == 1:
            draw.text(
                (local_cx, local_cy),
                text,
                font=single_font,
                fill=rgb_color,
                anchor="mm",
            )
        else:
            if text not in multi_font_cache:
                ref = ref_cell_size
                lines, size = fit_multiline(self._loader, ref, ref, text)
                multi_font_cache[text] = (lines, self._loader(size))
            lines, font = multi_font_cache[text]
            band_h = cell_h / len(lines)
            top_y = local_cy - cell_h / 2
            for i, line in enumerate(lines):
                draw.text(
                    (local_cx, top_y + (i + 0.5) * band_h),
                    line,
                    font=font,
                    fill=rgb_color,
                    anchor="mm",
                )

        result[y0:y1, x0:x1] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def _draw_centered_icon(self, image: np.ndarray) -> np.ndarray:
        """Alpha-blend the app icon centered on *image* (used for the blank state)."""
        h, w = image.shape[:2]
        icon_h, icon_w = self._icon_bgra.shape[:2]
        size = min(icon_w, icon_h, int(min(w, h) * _BLANK_ICON_SIZE_FRAC))
        if size <= 0:
            return image
        icon = cv2.resize(self._icon_bgra, (size, size), interpolation=cv2.INTER_AREA)
        x0, y0 = (w - size) // 2, (h - size) // 2
        result = image.copy()
        region = result[y0 : y0 + size, x0 : x0 + size].astype(np.float32)
        alpha = icon[:, :, 3:4].astype(np.float32) / 255.0
        fg = icon[:, :, :3].astype(np.float32)
        blended = fg * alpha + region * (1 - alpha)
        result[y0 : y0 + size, x0 : x0 + size] = blended.round().astype(np.uint8)
        return result
