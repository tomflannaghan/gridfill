"""Interactive grid editor: display a grid on its background image and edit cells."""

from __future__ import annotations

import importlib.resources
import os
import tkinter as tk
import tkinter.colorchooser
import tkinter.filedialog
import tkinter.simpledialog
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk

from .detection import detect_grids
from .document import CWD_EXTENSION, load_document, save_document
from .fonts import FontT, _best_grid, fit_font_size, fit_font_size_multi, font_loader
from .geometry import (
    bounding_rect,
    inset_quad,
    point_in_polygon,
    polygon_size,
    polygon_to_pixels,
)
from .io import ImageSource, load_image, save_image
from .preprocess import binarize, to_grayscale
from .types import Cell, CellKind, Direction, Grid

_KEYSYM_TO_DIRECTION = {
    "Up": Direction.UP,
    "Down": Direction.DOWN,
    "Left": Direction.LEFT,
    "Right": Direction.RIGHT,
}

_SELECTION_BGR = (255, 180, 0)
_DEFAULT_HIGHLIGHT_COLOR_BGR = (0, 255, 255)
_ACTIVE_GRID_BGR = (0, 180, 0)
_WHITE_DISTANCE_THRESHOLD = 30
_MAX_DISPLAY_SIZE = 900  # initial window size cap, before the user has resized it
_RESIZE_DEBOUNCE_MS = 80
_CELL_FILL_INSET_FRAC = 0.06
_BLANK_IMAGE_SIZE = (800, 600)  # (width, height), used when starting with no file
_CANVAS_BG_HEX = "#d9d9d9"  # Tk's classic widget grey, used for canvas letterboxing
_CANVAS_BG_BGR = (217, 217, 217)  # same colour as _CANVAS_BG_HEX, for compositing
_BLANK_ICON_SIZE_FRAC = 0.4  # fraction of the shorter canvas side the blank-state icon spans
_APP_ICON = importlib.resources.files("gridfill.assets").joinpath("icon.png")

_OPEN_FILETYPES = [
    (
        "Crossword document, image, or PDF",
        f"*{CWD_EXTENSION} *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.pdf",
    ),
    ("Crossword document", f"*{CWD_EXTENSION}"),
    ("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
    ("PDF", "*.pdf"),
    ("All files", "*.*"),
]


@dataclass
class _GridState:
    """Per-grid data needed by the editor.

    Two font sets are kept: one fitted to the full source resolution (used
    only when rendering for export/save) and one fitted to the downscaled
    display resolution (used for the interactive view, which is redrawn on
    every keystroke and must stay cheap).
    """

    grid: Grid
    single_font: ImageFont.FreeTypeFont
    ref_cell_size: tuple[int, int]
    display_single_font: ImageFont.FreeTypeFont
    display_ref_cell_size: tuple[int, int]
    multi_font_cache: dict[tuple[int, int], ImageFont.FreeTypeFont] = field(default_factory=dict)
    display_multi_font_cache: dict[tuple[int, int], ImageFont.FreeTypeFont] = field(
        default_factory=dict
    )


_SavePath = str | os.PathLike[str] | None


def _blank_image() -> np.ndarray:
    w, h = _BLANK_IMAGE_SIZE
    return np.full((h, w, 3), _CANVAS_BG_BGR, dtype=np.uint8)


def _default_save_name(input_path: _SavePath, extension: str) -> str | None:
    """Suggest a save-dialog filename: the input's basename with *extension* swapped in."""
    if input_path is None:
        return None
    stem = os.path.splitext(os.path.basename(os.fspath(input_path)))[0]
    return stem + extension


def _load_source(
    source: ImageSource | None,
) -> tuple[np.ndarray, list[Grid], _SavePath, list[tuple[float, float, str]]]:
    """Resolve *source* into ``(image, grids, save_path, annotations)``.

    *source* may be ``None`` (start blank), an already-loaded image array, an
    image path to detect grids from, or the path to a ``.cwd`` document
    previously written by this editor, which resumes with its saved grids and
    annotations.
    """
    if source is None:
        return _blank_image(), [], None, []

    if isinstance(source, np.ndarray):
        image = source.copy()
        binary = binarize(to_grayscale(image))
        return image, detect_grids(binary), None, []

    if os.fspath(source).endswith(CWD_EXTENSION):
        document = load_document(source)
        return document.image, document.grids, source, document.annotations

    image = load_image(source).copy()
    binary = binarize(to_grayscale(image))
    return image, detect_grids(binary), None, []


def _fit_font(
    grid: Grid,
    image_size: tuple[int, int],
    loader: Callable[[int], FontT],
) -> tuple[ImageFont.FreeTypeFont, tuple[int, int]]:
    sample_px = polygon_to_pixels(grid.cells[0].polygon, image_size)
    ref_w, ref_h = polygon_size(sample_px)
    return loader(fit_font_size(loader, ref_w, ref_h)), (ref_w, ref_h)


def _make_grid_states(
    grids: list[Grid],
    src_size: tuple[int, int],
    loader: Callable[[int], FontT],
) -> list[_GridState]:
    """Build per-grid state with full-resolution (export) fonts fitted.

    Display-resolution fonts are filled in separately by
    :func:`_fit_display_fonts` once the display size is known, and refitted
    again whenever the window is resized.
    """
    grid_states: list[_GridState] = []
    for grid in grids:
        single_font, ref_cell_size = _fit_font(grid, src_size, loader)
        grid_states.append(
            _GridState(
                grid=grid,
                single_font=single_font,
                ref_cell_size=ref_cell_size,
                # Placeholders, overwritten by _fit_display_fonts before use.
                display_single_font=single_font,
                display_ref_cell_size=ref_cell_size,
            )
        )
    return grid_states


def _fit_display_fonts(
    grid_states: list[_GridState],
    display_size: tuple[int, int],
    loader: Callable[[int], FontT],
) -> None:
    for gs in grid_states:
        gs.display_single_font, gs.display_ref_cell_size = _fit_font(gs.grid, display_size, loader)
        gs.display_multi_font_cache = {}


def _fit_display_size(
    src_w: int, src_h: int, box_w: int, box_h: int, *, allow_upscale: bool
) -> tuple[int, int]:
    """Fit (src_w, src_h) into (box_w, box_h), preserving aspect ratio.

    When *allow_upscale* is ``False`` the image is never enlarged past its
    native resolution (used for the very first window before it has a real
    size); a live window resize passes ``True`` so the image grows to match.
    """
    ratios = [box_w / max(1, src_w), box_h / max(1, src_h)]
    if not allow_upscale:
        ratios.append(1.0)
    scale = min(ratios)
    return max(1, round(src_w * scale)), max(1, round(src_h * scale))


def edit_grid(
    source: ImageSource | None = None,
    out_path: str | os.PathLike[str] | None = None,
    font_path: str | os.PathLike[str] | None = None,
    color: tuple[int, int, int] = (0, 0, 0),
) -> list[Grid]:
    """Open an interactive editor for all grids found in *source*.

    *source* is either an image (a path, an already-loaded array, or a PDF --
    whose last page is rendered at print resolution) to detect grids from,
    the path to a ``.cwd`` document previously written by this editor (which
    resumes editing with its saved grids and annotations), or ``None`` to
    start with a blank editor -- use File > Open to load an image, PDF, or
    document once it's running.

    Each grid gets its own editing state. Click a cell to select its grid.

    Returns a list of edited :class:`Grid` objects (one per grid); each is a
    :class:`RectangularGrid` or :class:`IrregularGrid` depending on what was detected.
    """
    image, grids, save_path, annotations = _load_source(source)
    loader = font_loader(font_path)
    input_path = None if source is None or isinstance(source, np.ndarray) else source

    editor = _GridEditor(
        image=image,
        grids=grids,
        loader=loader,
        color=color,
        out_path=out_path,
        save_path=save_path,
        input_path=input_path,
        annotations=annotations,
        is_blank=source is None,
    )
    editor.mainloop()
    return [gs.grid for gs in editor._grid_states]


def click_to_cell(
    click_x: float,
    click_y: float,
    scale: float,
    image_size: tuple[int, int],
    cells: list[Cell],
) -> int | None:
    """Map a display-space click to a flat index into *cells*, or ``None``."""
    sx = click_x / scale
    sy = click_y / scale
    for i, cell in enumerate(cells):
        polygon_px = polygon_to_pixels(cell.polygon, image_size)
        if point_in_polygon(sx, sy, polygon_px):
            return i
    return None


class _GridEditor(tk.Tk):
    """Tkinter application for interactive grid editing."""

    def __init__(
        self,
        image: np.ndarray,
        grids: list[Grid],
        loader: Callable[[int], FontT],
        color: tuple[int, int, int],
        out_path: str | os.PathLike[str] | None,
        save_path: str | os.PathLike[str] | None = None,
        input_path: str | os.PathLike[str] | None = None,
        annotations: list[tuple[float, float, str]] | None = None,
        is_blank: bool = False,
    ) -> None:
        super().__init__()
        self.title("Gridfill")
        with importlib.resources.as_file(_APP_ICON) as icon_path:
            icon_image = Image.open(icon_path).convert("RGBA")
            self._icon_photo = ImageTk.PhotoImage(icon_image)
            self._icon_bgra = cv2.cvtColor(np.array(icon_image), cv2.COLOR_RGBA2BGRA)
        self.iconphoto(True, cast(tk.PhotoImage, self._icon_photo))

        self._color = color
        self._highlight_color = _DEFAULT_HIGHLIGHT_COLOR_BGR
        self._out_path = out_path
        self._loader = loader
        self._resize_job: str | None = None
        self._last_canvas_box: tuple[int, int] | None = None
        self._has_loaded = False
        self._is_blank = False

        self._canvas = tk.Canvas(self, bg=_CANVAS_BG_HEX, highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._photo: ImageTk.PhotoImage | None = None
        self._canvas_image = self._canvas.create_image(0, 0, anchor=tk.NW)

        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self.bind("<Key>", self._on_key)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_menu()
        self._load_state(image, grids, save_path, input_path, annotations, is_blank=is_blank)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_state(
        self,
        image: np.ndarray,
        grids: list[Grid],
        save_path: str | os.PathLike[str] | None,
        input_path: str | os.PathLike[str] | None,
        annotations: list[tuple[float, float, str]] | None,
        *,
        is_blank: bool = False,
    ) -> None:
        """(Re)initialize all editing state from a freshly loaded image/grids.

        Used both for the initial load and for File > Open, which replaces
        the current session entirely.

        The interactive view is rendered against a copy of *image* downscaled
        to the display size -- this keeps per-keystroke rendering cheap even
        for large scans/PDF pages. Export and ``.cwd`` saves always work from
        the untouched full-resolution *image*.
        """
        self._image = image
        self._save_path = save_path
        self._input_path = input_path
        self._is_blank = is_blank

        src_h, src_w = image.shape[:2]
        self._src_size = (src_w, src_h)
        self._grid_states = _make_grid_states(grids, self._src_size, self._loader)

        self._active_grid_index: int | None = 0 if len(grids) == 1 else None
        # Flat index into the active grid's ``cells`` list, or None.
        self._selected: int | None = None
        self._multi_entry = False
        self._annotations: list[tuple[float, float, str]] = list(annotations or [])

        # Before the window has ever been shown, fall back to the initial
        # size cap and let the window grow to fit it -- the canvas' own
        # reported size can't be trusted yet (Tk gives it a nonzero default
        # even unmapped). Otherwise (a fresh File > Open into an
        # already-open editor) fit the new image into whatever size the
        # user currently has the window at.
        bootstrapping = not self._has_loaded
        self._has_loaded = True
        if bootstrapping:
            box_w, box_h = _MAX_DISPLAY_SIZE, _MAX_DISPLAY_SIZE
        else:
            self.update_idletasks()
            box_w, box_h = self._canvas.winfo_width(), self._canvas.winfo_height()
        self._refit_display(
            box_w, box_h, allow_upscale=not bootstrapping, resize_window=bootstrapping
        )

    def _refit_display(
        self, box_w: int, box_h: int, *, allow_upscale: bool, resize_window: bool = False
    ) -> None:
        """Recompute the downscaled display image/fonts to fit a (box_w, box_h) canvas.

        Called on load and whenever the window is resized, so the interactive
        view always matches the available canvas space.
        """
        src_w, src_h = self._src_size
        display_w, display_h = _fit_display_size(
            src_w, src_h, box_w, box_h, allow_upscale=allow_upscale
        )
        self._display_w = display_w
        self._display_h = display_h
        self._display_size = (display_w, display_h)
        self._scale = display_w / src_w

        if resize_window:
            self._canvas.config(width=display_w, height=display_h)

        if (display_w, display_h) == (src_w, src_h):
            self._display_image = self._image
        else:
            interp = cv2.INTER_AREA if display_w <= src_w else cv2.INTER_CUBIC
            self._display_image = cv2.resize(
                self._image, (display_w, display_h), interpolation=interp
            )

        _fit_display_fonts(self._grid_states, self._display_size, self._loader)
        self._base_image_display = self._compute_base_image(self._display_image, self._grid_states)
        self._render_and_display()

    def _on_canvas_resize(self, event: tk.Event[tk.Canvas]) -> None:
        box = (event.width, event.height)
        if box == self._last_canvas_box:
            return
        self._last_canvas_box = box
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(_RESIZE_DEBOUNCE_MS, lambda: self._finish_resize(box))

    def _finish_resize(self, box: tuple[int, int]) -> None:
        self._resize_job = None
        self._refit_display(*box, allow_upscale=True)

    @property
    def _active(self) -> _GridState | None:
        if self._active_grid_index is None:
            return None
        return self._grid_states[self._active_grid_index]

    def _find_click_target(self, event_x: float, event_y: float) -> tuple[int, int] | None:
        """Return ``(grid_index, cell_index)`` or ``None``."""
        for gi, gs in enumerate(self._grid_states):
            idx = click_to_cell(event_x, event_y, self._scale, self._src_size, gs.grid.cells)
            if idx is not None:
                return (gi, idx)
        return None

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open…", accelerator="Ctrl+O", command=self._open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self._save_document)
        file_menu.add_command(
            label="Export Image…",
            accelerator="Ctrl+Shift+S",
            command=self._save_image,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(
            label="Clear Cell",
            accelerator="Delete",
            command=self._clear_selected_cell,
        )
        edit_menu.add_command(label="Deselect", accelerator="Escape", command=self._deselect)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        text_menu = tk.Menu(menubar, tearoff=0)
        text_menu.add_command(label="Clear All Text", command=self._clear_annotations)
        menubar.add_cascade(label="Text", menu=text_menu)

        highlight_menu = tk.Menu(menubar, tearoff=0)
        highlight_menu.add_command(
            label="Highlight Cell",
            accelerator="Ctrl+H",
            command=self._toggle_highlight,
        )
        highlight_menu.add_command(
            label="Highlight Colour…",
            accelerator="Ctrl+Shift+H",
            command=self._pick_highlight_color,
        )
        menubar.add_cascade(label="Highlight", menu=highlight_menu)

        self.config(menu=menubar)

    def _clear_selected_cell(self) -> None:
        gs = self._active
        if gs is None or self._selected is None:
            return
        cell = gs.grid.cells[self._selected]
        cell.letter = None
        cell.kind = CellKind.EMPTY
        self._render_and_display()

    def _deselect(self) -> None:
        self._selected = None
        self._multi_entry = False
        self._render_and_display()

    # ------------------------------------------------------------------
    # Base image (backgrounds + highlights for all grids)
    # ------------------------------------------------------------------

    @staticmethod
    def _cell_highlight_color(cell: Cell) -> tuple[int, int, int] | None:
        bg = cell.background
        if bg is None:
            return None
        dist = sum((a - 255) ** 2 for a in bg)
        if dist < _WHITE_DISTANCE_THRESHOLD**2:
            return None
        return bg

    @classmethod
    def _compute_base_image(
        cls,
        image: np.ndarray,
        grid_states: list[_GridState],
    ) -> np.ndarray:
        src_h, src_w = image.shape[:2]
        result = image.astype(np.float32).copy()

        for gs in grid_states:
            for cell in gs.grid.cells:
                if cell.kind is CellKind.BLOCK:
                    continue
                bg = cls._cell_highlight_color(cell)
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

    def _recompute_base(self) -> None:
        """Refresh the display-resolution base image.

        The full-resolution base is recomputed on demand at export time
        (see :meth:`_render`), so there is nothing to refresh here for it.
        """
        self._base_image_display = self._compute_base_image(self._display_image, self._grid_states)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw_letter_in_cell(
        self,
        result: np.ndarray,
        cell: Cell,
        image_size: tuple[int, int],
        single_font: ImageFont.FreeTypeFont,
        ref_cell_size: tuple[int, int],
        multi_font_cache: dict[tuple[int, int], ImageFont.FreeTypeFont],
    ) -> None:
        text = (cell.letter or "").upper()
        if not text:
            return
        polygon_px = polygon_to_pixels(cell.polygon, image_size)
        cell_w, cell_h = polygon_size(polygon_px)
        cx, cy = polygon_px.mean(axis=0)

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
            ref_w, ref_h = ref_cell_size
            grid_shape = _best_grid(len(text), ref_w, ref_h)
            if grid_shape not in multi_font_cache:
                size = fit_font_size_multi(self._loader, ref_w, ref_h, grid_shape[0], grid_shape[1])
                multi_font_cache[grid_shape] = self._loader(size)
            font = multi_font_cache[grid_shape]
            nrows, ncols = grid_shape
            slot_w, slot_h = cell_w / ncols, cell_h / nrows
            top_left_x, top_left_y = local_cx - cell_w / 2, local_cy - cell_h / 2
            for i, ch in enumerate(text):
                ri, ci = divmod(i, ncols)
                draw.text(
                    (top_left_x + (ci + 0.5) * slot_w, top_left_y + (ri + 0.5) * slot_h),
                    ch,
                    font=font,
                    fill=rgb_color,
                    anchor="mm",
                )

        result[y0:y1, x0:x1] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def _render(self, *, for_save: bool = False) -> np.ndarray:
        if for_save:
            base = self._compute_base_image(self._image, self._grid_states)
            image_size = self._src_size
        else:
            base = self._base_image_display
            image_size = self._display_size
        result = base.copy()

        if not for_save and self._is_blank:
            result = self._draw_centered_icon(result)

        for gs in self._grid_states:
            single_font, ref_cell_size, multi_font_cache = (
                (gs.single_font, gs.ref_cell_size, gs.multi_font_cache)
                if for_save
                else (gs.display_single_font, gs.display_ref_cell_size, gs.display_multi_font_cache)
            )
            for cell in gs.grid.cells:
                if cell.kind is CellKind.LETTER and cell.letter:
                    self._draw_letter_in_cell(
                        result, cell, image_size, single_font, ref_cell_size, multi_font_cache
                    )

        # Active grid indicator
        if not for_save and self._active_grid_index is not None and len(self._grid_states) > 1:
            gs = self._grid_states[self._active_grid_index]
            hull_px = polygon_to_pixels(gs.grid.bounding_polygon(), image_size).astype(np.int32)
            cv2.polylines(result, [hull_px], True, _ACTIVE_GRID_BGR, 2)

        # Cell selection highlight
        if not for_save and self._selected is not None and self._active_grid_index is not None:
            gs = self._grid_states[self._active_grid_index]
            cell = gs.grid.cells[self._selected]
            poly_px = polygon_to_pixels(cell.polygon, image_size).astype(np.int32)
            thickness = 3 if self._multi_entry else 2
            cv2.polylines(result, [poly_px], True, _SELECTION_BGR, thickness)

        # Text annotations -- stored in full-source pixel coordinates, so
        # scale them down to display space when not rendering for export.
        if self._annotations:
            gs = self._active or self._grid_states[0]
            font = gs.single_font if for_save else gs.display_single_font
            coord_scale = 1.0 if for_save else self._scale
            pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            b, g, r = self._color
            rgb_color = (r, g, b)
            for ax, ay, text in self._annotations:
                draw.text(
                    (ax * coord_scale, ay * coord_scale),
                    text,
                    font=font,
                    fill=rgb_color,
                    anchor="ls",
                )
            result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        return result

    def _render_and_display(self) -> None:
        rendered = self._render()
        rgb = cv2.cvtColor(rendered, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self._photo = ImageTk.PhotoImage(pil_img)
        self._canvas.itemconfig(self._canvas_image, image=self._photo)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_click(self, event: tk.Event[tk.Canvas]) -> None:
        target = self._find_click_target(event.x, event.y)
        if target is not None:
            gi, idx = target
            cell = self._grid_states[gi].grid.cells[idx]
            if cell.kind is CellKind.BLOCK:
                self._active_grid_index = gi
                self._selected = None
                self._multi_entry = False
                self._render_and_display()
                return
            self._active_grid_index = gi
            self._selected = idx
        else:
            self._selected = None
        self._multi_entry = False
        self._render_and_display()

    def _on_double_click(self, event: tk.Event[tk.Canvas]) -> None:
        target = self._find_click_target(event.x, event.y)
        if target is None:
            self._add_annotation(event.x, event.y)
            return
        gi, idx = target
        cell = self._grid_states[gi].grid.cells[idx]
        if cell.kind is CellKind.BLOCK:
            return
        self._active_grid_index = gi
        self._selected = idx
        self._multi_entry = True
        self._render_and_display()

    def _on_key(self, event: tk.Event[tk.Misc]) -> None:
        if event.keysym == "Escape":
            if self._multi_entry:
                self._multi_entry = False
                self._render_and_display()
            else:
                self._deselect()
            return

        if event.keysym == "Return":
            if self._multi_entry:
                self._multi_entry = False
                self._render_and_display()
            return

        state = event.state if isinstance(event.state, int) else 0
        ctrl = bool(state & 0x4)
        shift = bool(state & 0x1)

        if ctrl and event.keysym.lower() == "o":
            self._open_file()
            return

        if ctrl and event.keysym.lower() == "s":
            if shift:
                self._save_image()
            else:
                self._save_document()
            return

        if ctrl and event.keysym.lower() == "h":
            if shift:
                self._pick_highlight_color()
            else:
                self._toggle_highlight()
            return

        gs = self._active
        if gs is None or self._selected is None:
            return

        index = self._selected

        if event.keysym in _KEYSYM_TO_DIRECTION:
            self._multi_entry = False
            self._move_selection(event.keysym)
            return

        if event.keysym == "BackSpace":
            cell = gs.grid.cells[index]
            if self._multi_entry and cell.letter and len(cell.letter) > 1:
                cell.letter = cell.letter[:-1]
            elif cell.kind is CellKind.LETTER:
                cell.letter = None
                cell.kind = CellKind.EMPTY
            else:
                self._retreat_selection()
                self._clear_selected_cell()
            self._render_and_display()
            return

        if event.keysym == "Delete":
            self._clear_selected_cell()
            return

        ch = event.char.upper()
        if ch and ch.isalnum() and len(ch) == 1:
            cell = gs.grid.cells[index]
            if self._multi_entry:
                cell.letter = (cell.letter or "") + ch
            else:
                cell.letter = ch
            cell.kind = CellKind.LETTER
            if not self._multi_entry:
                self._advance_selection()
            self._render_and_display()

    def _move_selection(self, keysym: str) -> None:
        """Move the selection to the cell adjacent in the arrow-key direction.

        The geometry of "adjacent" is the grid's own concern (see
        :meth:`Grid.neighbor`), so this works for any grid shape."""
        gs = self._active
        if gs is None or self._selected is None:
            return
        target = gs.grid.neighbor(self._selected, _KEYSYM_TO_DIRECTION[keysym])
        if target is not None:
            self._selected = target
            self._render_and_display()

    def _advance_selection(self) -> None:
        """Move to the next non-block cell in reading order, without wrapping
        back to the grid's start once the last cell is passed."""
        gs = self._active
        if gs is None or self._selected is None:
            return
        cells = gs.grid.cells
        index = self._selected
        while index + 1 < len(cells):
            index += 1
            if cells[index].kind is not CellKind.BLOCK:
                self._selected = index
                return

    def _retreat_selection(self) -> None:
        """Move to the previous non-block cell in reading order, without wrapping
        back to the grid's end once the first cell is passed."""
        gs = self._active
        if gs is None or self._selected is None:
            return
        cells = gs.grid.cells
        index = self._selected
        while index > 0:
            index -= 1
            if cells[index].kind is not CellKind.BLOCK:
                self._selected = index
                return

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    def _add_annotation(self, display_x: float, display_y: float) -> None:
        text = tkinter.simpledialog.askstring("Add Text", "Enter text:", parent=self)
        if not text:
            return
        src_x = display_x / self._scale
        src_y = display_y / self._scale
        self._annotations.append((src_x, src_y, text))
        self._render_and_display()

    def _clear_annotations(self) -> None:
        self._annotations.clear()
        self._render_and_display()

    # ------------------------------------------------------------------
    # Highlighting
    # ------------------------------------------------------------------

    def _toggle_highlight(self) -> None:
        gs = self._active
        if gs is None or self._selected is None:
            return
        cell = gs.grid.cells[self._selected]
        if cell.kind is CellKind.BLOCK:
            return
        if cell.background == self._highlight_color:
            cell.background = None
        else:
            cell.background = self._highlight_color
        self._recompute_base()
        self._render_and_display()

    def _pick_highlight_color(self) -> None:
        b, g, r = self._highlight_color
        result = tkinter.colorchooser.askcolor(
            color=f"#{r:02x}{g:02x}{b:02x}",
            title="Pick highlight colour",
        )
        if result[0] is None:
            return
        rgb = result[0]
        self._highlight_color = (int(rgb[2]), int(rgb[1]), int(rgb[0]))

    # ------------------------------------------------------------------
    # Open / Save
    # ------------------------------------------------------------------

    def _open_file(self) -> None:
        path = tkinter.filedialog.askopenfilename(filetypes=_OPEN_FILETYPES)
        if not path:
            return
        image, grids, save_path, annotations = _load_source(path)
        self._load_state(image, grids, save_path, path, annotations)
        self.title(f"Gridfill — opened {os.path.basename(path)}")

    def _save_image(self) -> None:
        path = self._out_path
        if path is None:
            path = tkinter.filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=_default_save_name(self._input_path, ".png") or "",
                filetypes=[
                    ("PNG", "*.png"),
                    ("JPEG", "*.jpg"),
                    ("All files", "*.*"),
                ],
            )
        if not path:
            return
        rendered = self._render(for_save=True)
        save_image(path, rendered)
        self._out_path = path
        self.title(f"Gridfill — exported {os.path.basename(str(path))}")

    def _save_document(self) -> None:
        path = self._save_path
        if path is None:
            path = tkinter.filedialog.asksaveasfilename(
                defaultextension=CWD_EXTENSION,
                initialfile=_default_save_name(self._input_path, CWD_EXTENSION) or "",
                filetypes=[
                    ("Crossword document", f"*{CWD_EXTENSION}"),
                    ("All files", "*.*"),
                ],
            )
        if not path:
            return
        grids = [gs.grid for gs in self._grid_states]
        save_document(path, self._image, grids, self._annotations)
        self._save_path = path
        self.title(f"Gridfill — saved {os.path.basename(str(path))}")

    def _on_close(self) -> None:
        self.destroy()
