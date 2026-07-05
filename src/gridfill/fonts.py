"""Font loading and cell-fitting helpers for rendering letters into grid cells."""

from __future__ import annotations

import importlib.resources
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

# Bundled as a last resort so the editor works even where none of the above
# system fonts are installed -- notably on Windows, and inside a PyInstaller
# build, which has no system font directory to fall back on.
_BUNDLED_FONT = importlib.resources.files("gridfill.assets.fonts").joinpath("DejaVuSans.ttf")


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
        with importlib.resources.as_file(_BUNDLED_FONT) as bundled_path:
            chosen = str(bundled_path)

    return lambda size: ImageFont.truetype(chosen, size)


def fit_font_size(
    loader: Callable[[int], FontT],
    cell_width: int,
    cell_height: int,
    height_ratio: float = 0.5,
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


def split_lines(text: str, nrows: int) -> list[str]:
    """Split *text* into *nrows* contiguous lines, as evenly as possible.

    Order is preserved and earlier lines take the surplus, so a 5-character
    string over 2 rows becomes ``["ABC", "DE"]``.
    """
    base, extra = divmod(len(text), nrows)
    lines: list[str] = []
    i = 0
    for r in range(nrows):
        length = base + (1 if r < extra else 0)
        lines.append(text[i : i + length])
        i += length
    return lines


def fit_multiline(
    loader: Callable[[int], FontT],
    cell_width: int,
    cell_height: int,
    text: str,
    height_ratio: float = 0.5,
    margin: float = 0.78,
) -> tuple[list[str], int]:
    """Lay *text* out over one or more lines of adjacent characters.

    Each line's characters sit side by side (no per-glyph slots). Every row
    count is tried and the one yielding the largest font size wins, where the
    size is bounded by the cell height (all lines must fit) and the widest
    line's ink width (it must fit ``margin`` of the cell width). Ties favour
    fewer lines, so text is only wrapped when doing so genuinely permits larger
    glyphs. Returns the chosen lines and font size.
    """
    probe = 100
    font = loader(probe)
    _, cap_top, _, cap_bottom = font.getbbox("H")
    cap_h = max(1, cap_bottom - cap_top)

    best_lines = [text]
    best_size = 0
    for nrows in range(1, len(text) + 1):
        lines = split_lines(text, nrows)
        size_h = probe * (height_ratio * cell_height / nrows) / cap_h
        widest = max(_ink_width(font, line) for line in lines)
        size_w = probe * (margin * cell_width) / widest
        size = int(min(size_h, size_w))
        if size > best_size:
            best_size = size
            best_lines = lines
    return best_lines, max(8, best_size)


def _ink_width(font: FontT, text: str) -> int:
    """Pixel width of *text*'s ink bounding box in *font* (min 1)."""
    left, _, right, _ = font.getbbox(text)
    return max(1, int(right - left))
