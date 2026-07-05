"""Tests for the Tk-free GridRenderer.

Extracting rendering out of the Tk editor makes exactly this possible: exercise
the image composition directly, with no display.
"""

from __future__ import annotations

import numpy as np

from gridfill.fonts import font_loader
from gridfill.renderer import GridLayer, GridRenderer
from gridfill.types import Cell, CellKind, RectangularGrid

# A 200x100 image split into two square cells side by side.
_IMAGE_SIZE = (200, 100)


def _two_cell_grid() -> RectangularGrid:
    cells = [
        Cell(polygon=[(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)]),
        Cell(polygon=[(0.5, 0.0), (1.0, 0.0), (1.0, 1.0), (0.5, 1.0)]),
    ]
    return RectangularGrid(rows=1, cols=2, cells=cells)


def _renderer() -> GridRenderer:
    icon = np.zeros((16, 16, 4), dtype=np.uint8)
    return GridRenderer(color=(0, 0, 0), loader=font_loader(None), icon_bgra=icon)


def _white_base() -> np.ndarray:
    h, w = _IMAGE_SIZE[1], _IMAGE_SIZE[0]
    return np.full((h, w, 3), 255, dtype=np.uint8)


def _layer(grid: RectangularGrid) -> GridLayer:
    return GridLayer(grid, font_loader(None)(40), ref_cell_size=40, multi_font_cache={})


def test_render_draws_letter_in_its_cell_only() -> None:
    grid = _two_cell_grid()
    grid.cells[0].kind = CellKind.LETTER
    grid.cells[0].letter = "A"

    out = _renderer().render(
        _white_base(), _IMAGE_SIZE, [_layer(grid)], annotations=[], annotation_font=None
    )

    left, right = out[:, :100], out[:, 100:]
    assert left.min() < 128  # black glyph drawn in the left cell
    assert (right == 255).all()  # right cell untouched


def test_compute_base_image_fills_highlighted_cell() -> None:
    grid = _two_cell_grid()
    grid.cells[1].background = (0, 0, 255)  # red fill (BGR)

    out = _renderer().compute_base_image(_white_base(), [grid])

    assert (out[:, :100] == 255).all()  # unhighlighted cell stays white
    b, g, r = out[50, 150]  # centre of the highlighted cell
    assert b < 50 and g < 50 and r > 200


def test_render_draws_annotation() -> None:
    grid = _two_cell_grid()
    font = font_loader(None)(20)

    out = _renderer().render(
        _white_base(),
        _IMAGE_SIZE,
        [_layer(grid)],
        annotations=[(0.5, 0.5, "HI")],
        annotation_font=font,
    )

    assert out.min() < 128  # annotation text drawn somewhere


def test_render_without_content_returns_base_unchanged() -> None:
    base = _white_base()
    out = _renderer().render(
        base, _IMAGE_SIZE, [_layer(_two_cell_grid())], annotations=[], annotation_font=None
    )
    assert np.array_equal(out, base)
