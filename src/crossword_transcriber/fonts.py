"""Font loading and cell-fitting helpers for the write pipeline."""

from __future__ import annotations

import os
from collections.abc import Callable

from PIL import ImageFont

FontT = ImageFont.FreeTypeFont

# Common scalable fonts to try when the caller doesn't supply one. The bare
# names let Pillow/freetype resolve them from standard font directories.
_FALLBACK_FONTS = (
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Regular.ttf",
    "Arial.ttf",
)


def font_loader(font_path: str | os.PathLike[str] | None) -> Callable[[int], FontT]:
    """Return a ``size -> font`` loader for the requested (or a fallback) font.

    Resolves the font once so a clear error is raised up front if none is found,
    then returns a cheap loader the sizing code can call at different sizes.
    """
    candidates = [os.fspath(font_path)] if font_path is not None else list(_FALLBACK_FONTS)

    chosen: str | None = None
    for name in candidates:
        try:
            ImageFont.truetype(name, 12)
        except OSError:
            continue
        chosen = name
        break

    if chosen is None:
        raise OSError(
            "No usable TrueType font found; pass font_path explicitly. "
            f"Tried: {', '.join(candidates)}"
        )

    return lambda size: ImageFont.truetype(chosen, size)


def fit_font_size(
    loader: Callable[[int], FontT],
    cell_width: int,
    cell_height: int,
    height_ratio: float = 0.6,
    max_width_ratio: float = 0.85,
) -> int:
    """Pick a font size so an uppercase glyph fills the cell with margin.

    Sizes to ``height_ratio`` of the cell height using a reference cap-height
    glyph, then shrinks if the widest glyph would exceed ``max_width_ratio`` of
    the cell width. FreeType scales linearly, so a single correction suffices.
    """
    probe = 100
    left, top, right, bottom = loader(probe).getbbox("H")
    glyph_h = max(1, bottom - top)
    size = max(8, int(probe * (height_ratio * cell_height) / glyph_h))

    # Width clamp against a wide glyph.
    wl, _, wr, _ = loader(size).getbbox("W")
    glyph_w = max(1, wr - wl)
    if glyph_w > max_width_ratio * cell_width:
        size = max(8, int(size * (max_width_ratio * cell_width) / glyph_w))
    return size
