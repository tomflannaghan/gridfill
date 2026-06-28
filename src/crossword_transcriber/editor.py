"""Interactive grid editor: display a grid on its background image and edit cells."""

from __future__ import annotations

import os
import tkinter as tk
import tkinter.colorchooser
import tkinter.filedialog
import tkinter.simpledialog
from collections.abc import Callable
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk

from .detection import DetectedGrid, detect_grids
from .fonts import FontT, _best_grid, fit_font_size, fit_font_size_multi, font_loader
from .io import ImageSource, load_image, save_image
from .preprocess import binarize, to_grayscale
from .segmentation import infer_cell_boxes
from .types import BoundingBox, Cell, CellKind, Grid

_SELECTION_BGR = (255, 180, 0)
_HIGHLIGHT_BGR = (50, 50, 255)
_DEFAULT_HIGHLIGHT_COLOR_BGR = (0, 255, 255)
_ACTIVE_GRID_BGR = (0, 180, 0)
_WHITE_DISTANCE_THRESHOLD = 30
_MAX_DISPLAY_SIZE = 900


@dataclass
class _GridState:
    """Per-grid data needed by the editor."""

    detected: DetectedGrid
    boxes: list[list[BoundingBox]]
    grid: Grid
    inverse: np.ndarray
    single_font: ImageFont.FreeTypeFont
    multi_font_cache: dict[tuple[int, int], ImageFont.FreeTypeFont] = field(default_factory=dict)


def edit_grid(
    source: ImageSource,
    out_path: str | os.PathLike[str] | None = None,
    font_path: str | os.PathLike[str] | None = None,
    color: tuple[int, int, int] = (0, 0, 0),
    highlight_confidence: float | None = None,
) -> list[Grid]:
    """Open an interactive editor for all grids found in *source*.

    Each grid detected in the image gets its own editing state.  Click a cell
    to select its grid; Save CSV applies to the active grid.

    Returns a list of edited :class:`Grid` objects (one per detected grid).
    """
    image = load_image(source).copy()
    binary = binarize(to_grayscale(image))
    detected_list = detect_grids(binary)

    loader = font_loader(font_path)
    grid_states: list[_GridState] = []
    for detected in detected_list:
        boxes = infer_cell_boxes(detected.line_mask)
        rows, cols = len(boxes), len(boxes[0])
        cells = [[Cell(row=r, col=c, box=boxes[r][c]) for c in range(cols)] for r in range(rows)]
        grid = Grid(rows=rows, cols=cols, cells=cells, transform=detected.transform)
        inverse = np.linalg.inv(detected.transform)
        sample = boxes[0][0]
        single_font = loader(fit_font_size(loader, sample.width, sample.height))
        grid_states.append(
            _GridState(
                detected=detected,
                boxes=boxes,
                grid=grid,
                inverse=inverse,
                single_font=single_font,
            )
        )

    editor = _GridEditor(
        image=image,
        grid_states=grid_states,
        loader=loader,
        color=color,
        highlight_confidence=highlight_confidence,
        out_path=out_path,
    )
    editor.mainloop()
    return [gs.grid for gs in editor._grid_states]


def click_to_cell(
    click_x: float,
    click_y: float,
    scale: float,
    transform: np.ndarray,
    boxes: list[list[BoundingBox]],
) -> tuple[int, int] | None:
    """Map a display-space click to a grid cell, or ``None`` if outside."""
    sx = click_x / scale
    sy = click_y / scale
    pt = np.array([[[sx, sy]]], dtype=np.float32)
    rectified = cv2.perspectiveTransform(pt, transform)[0][0]
    rx, ry = float(rectified[0]), float(rectified[1])
    for r, row in enumerate(boxes):
        for c, box in enumerate(row):
            if box.x <= rx < box.x2 and box.y <= ry < box.y2:
                return (r, c)
    return None


class _GridEditor(tk.Tk):
    """Tkinter application for interactive grid editing."""

    def __init__(
        self,
        image: np.ndarray,
        grid_states: list[_GridState],
        loader: Callable[[int], FontT],
        color: tuple[int, int, int],
        highlight_confidence: float | None,
        out_path: str | os.PathLike[str] | None,
    ) -> None:
        super().__init__()
        self.title("Crossword Grid Editor")

        self._grid_states = grid_states
        self._color = color
        self._highlight_confidence = highlight_confidence
        self._highlight_color = _DEFAULT_HIGHLIGHT_COLOR_BGR
        self._out_path = out_path
        self._image = image
        self._loader = loader

        src_h, src_w = image.shape[:2]
        self._src_size = (src_w, src_h)

        self._base_image = self._compute_base_image(image, grid_states, highlight_confidence)

        scale = min(_MAX_DISPLAY_SIZE / src_w, _MAX_DISPLAY_SIZE / src_h, 1.0)
        self._display_w = int(src_w * scale)
        self._display_h = int(src_h * scale)
        self._scale = scale

        self._active_grid_index: int | None = 0 if len(grid_states) == 1 else None
        self._selected: tuple[int, int] | None = None
        self._multi_entry = False
        self._annotations: list[tuple[float, float, str]] = []

        self._canvas = tk.Canvas(self, width=self._display_w, height=self._display_h)
        self._canvas.pack()
        self._photo: ImageTk.PhotoImage | None = None
        self._canvas_image = self._canvas.create_image(0, 0, anchor=tk.NW)

        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Key>", self._on_key)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_menu()
        self._render_and_display()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _active(self) -> _GridState | None:
        if self._active_grid_index is None:
            return None
        return self._grid_states[self._active_grid_index]

    def _find_click_target(self, event_x: float, event_y: float) -> tuple[int, int, int] | None:
        """Return ``(grid_index, row, col)`` or ``None``."""
        for gi, gs in enumerate(self._grid_states):
            hit = click_to_cell(event_x, event_y, self._scale, gs.detected.transform, gs.boxes)
            if hit is not None:
                return (gi, hit[0], hit[1])
        return None

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save Image", accelerator="Ctrl+S", command=self._save_image)
        file_menu.add_command(
            label="Save as CSV",
            accelerator="Ctrl+Shift+S",
            command=self._save_csv,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Close", accelerator="Return", command=self._on_close)
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
        r, c = self._selected
        cell = gs.grid.cells[r][c]
        cell.letter = None
        cell.kind = CellKind.EMPTY
        cell.confidence = None
        self._render_and_display()

    def _deselect(self) -> None:
        self._selected = None
        self._multi_entry = False
        self._render_and_display()

    # ------------------------------------------------------------------
    # Base image (backgrounds + highlights for all grids)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_base_image(
        image: np.ndarray,
        grid_states: list[_GridState],
        highlight_confidence: float | None,
    ) -> np.ndarray:
        src_h, src_w = image.shape[:2]
        result = image.copy()

        for gs in grid_states:
            width, height = gs.detected.size
            line_mask_bool = gs.detected.line_mask > 0
            bg_layer = np.zeros((height, width, 3), dtype=np.uint8)
            bg_mask = np.zeros((height, width), dtype=np.uint8)

            for row_boxes, row_cells in zip(gs.boxes, gs.grid.cells, strict=True):
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
                warped_bg = cv2.warpPerspective(bg_layer, gs.inverse, (src_w, src_h))
                warped_mask = cv2.warpPerspective(bg_mask, gs.inverse, (src_w, src_h))
                alpha = (warped_mask.astype(np.float32) / 255.0)[:, :, None]
                result = np.asarray(
                    (result.astype(np.float32) * (1 - alpha) + warped_bg.astype(np.float32) * alpha)
                    .round()
                    .astype(np.uint8)
                )

        return result

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self, *, for_save: bool = False) -> np.ndarray:
        src_w, src_h = self._src_size
        fill = np.array(self._color, dtype=np.float32).reshape(1, 1, 3)
        result_f = self._base_image.astype(np.float32)

        for gs in self._grid_states:
            width, height = gs.detected.size
            letter_grid = gs.grid.to_letters()

            for lr in letter_grid:
                for lv in lr:
                    if lv and len(lv) > 1:
                        gr = _best_grid(len(lv), gs.boxes[0][0].width, gs.boxes[0][0].height)
                        if gr not in gs.multi_font_cache:
                            sz = fit_font_size_multi(
                                self._loader,
                                gs.boxes[0][0].width,
                                gs.boxes[0][0].height,
                                gr[0],
                                gr[1],
                            )
                            gs.multi_font_cache[gr] = self._loader(sz)

            mask = Image.new("L", (width, height), 0)
            draw = ImageDraw.Draw(mask)

            for row, letter_row in zip(gs.boxes, letter_grid, strict=True):
                for box, letter in zip(row, letter_row, strict=True):
                    if not letter:
                        continue
                    text = letter.upper()
                    if len(text) == 1:
                        cx = box.x + box.width / 2
                        cy = box.y + box.height / 2
                        draw.text(
                            (cx, cy),
                            text,
                            font=gs.single_font,
                            fill=255,
                            anchor="mm",
                        )
                    else:
                        ref = gs.boxes[0][0]
                        nrows, ncols = _best_grid(len(text), ref.width, ref.height)
                        font = gs.multi_font_cache[(nrows, ncols)]
                        slot_w = box.width / ncols
                        slot_h = box.height / nrows
                        for i, ch in enumerate(text):
                            ri = i // ncols
                            ci = i % ncols
                            cx = box.x + (ci + 0.5) * slot_w
                            cy = box.y + (ri + 0.5) * slot_h
                            draw.text(
                                (cx, cy),
                                ch,
                                font=font,
                                fill=255,
                                anchor="mm",
                            )

            warped = cv2.warpPerspective(np.array(mask), gs.inverse, (src_w, src_h))
            alpha = (warped.astype(np.float32) / 255.0)[:, :, None]
            result_f = result_f * (1 - alpha) + fill * alpha

        result = np.asarray(result_f.round().astype(np.uint8))

        # Active grid indicator
        if not for_save and self._active_grid_index is not None and len(self._grid_states) > 1:
            gs = self._grid_states[self._active_grid_index]
            rect_w, rect_h = gs.detected.size
            corners = np.array(
                [[[0, 0], [rect_w, 0], [rect_w, rect_h], [0, rect_h]]],
                dtype=np.float32,
            )
            src_corners = cv2.perspectiveTransform(corners, gs.inverse)[0].astype(np.int32)
            cv2.polylines(result, [src_corners], True, _ACTIVE_GRID_BGR, 3)

        # Cell selection highlight
        if not for_save and self._selected is not None and self._active_grid_index is not None:
            gs = self._grid_states[self._active_grid_index]
            r, c = self._selected
            box = gs.boxes[r][c]
            corners = np.array(
                [
                    [
                        [box.x, box.y],
                        [box.x2, box.y],
                        [box.x2, box.y2],
                        [box.x, box.y2],
                    ]
                ],
                dtype=np.float32,
            )
            src_corners = cv2.perspectiveTransform(corners, gs.inverse)[0].astype(np.int32)
            thickness = 5 if self._multi_entry else 3
            cv2.polylines(result, [src_corners], True, _SELECTION_BGR, thickness)

        # Text annotations
        if self._annotations:
            gs = self._active or self._grid_states[0]
            pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            b, g, r = self._color
            rgb_color = (r, g, b)
            for ax, ay, text in self._annotations:
                draw.text(
                    (ax, ay),
                    text,
                    font=gs.single_font,
                    fill=rgb_color,
                    anchor="ls",
                )
            result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        return result

    def _render_and_display(self) -> None:
        rendered = self._render()
        rgb = cv2.cvtColor(rendered, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        if (self._display_w, self._display_h) != (
            pil_img.width,
            pil_img.height,
        ):
            pil_img = pil_img.resize((self._display_w, self._display_h), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(pil_img)
        self._canvas.itemconfig(self._canvas_image, image=self._photo)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_click(self, event: tk.Event[tk.Canvas]) -> None:
        target = self._find_click_target(event.x, event.y)
        if target is not None:
            gi, r, c = target
            cell = self._grid_states[gi].grid.cells[r][c]
            if cell.kind is CellKind.BLOCK:
                self._active_grid_index = gi
                self._selected = None
                self._multi_entry = False
                self._render_and_display()
                return
            self._active_grid_index = gi
            self._selected = (r, c)
        else:
            self._selected = None
        self._multi_entry = False
        self._render_and_display()

    def _on_double_click(self, event: tk.Event[tk.Canvas]) -> None:
        target = self._find_click_target(event.x, event.y)
        if target is None:
            self._add_annotation(event.x, event.y)
            return
        gi, r, c = target
        cell = self._grid_states[gi].grid.cells[r][c]
        if cell.kind is CellKind.BLOCK:
            return
        self._active_grid_index = gi
        self._selected = (r, c)
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
            else:
                self._on_close()
            return

        state = event.state if isinstance(event.state, int) else 0
        ctrl = bool(state & 0x4)
        shift = bool(state & 0x1)

        if ctrl and event.keysym.lower() == "s":
            if shift:
                self._save_csv()
            else:
                self._save_image()
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

        r, c = self._selected

        if event.keysym in ("Up", "Down", "Left", "Right"):
            self._multi_entry = False
            self._move_selection(event.keysym)
            return

        if event.keysym == "BackSpace":
            cell = gs.grid.cells[r][c]
            if self._multi_entry and cell.letter and len(cell.letter) > 1:
                cell.letter = cell.letter[:-1]
            elif cell.kind is CellKind.LETTER:
                cell.letter = None
                cell.kind = CellKind.EMPTY
                cell.confidence = None
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
            cell = gs.grid.cells[r][c]
            if self._multi_entry:
                cell.letter = (cell.letter or "") + ch
            else:
                cell.letter = ch
            cell.kind = CellKind.LETTER
            cell.confidence = None
            if not self._multi_entry:
                self._advance_selection()
            self._render_and_display()

    def _move_selection(self, direction: str) -> None:
        gs = self._active
        if gs is None or self._selected is None:
            return
        r, c = self._selected
        dr = {"Up": -1, "Down": 1}.get(direction, 0)
        dc = {"Left": -1, "Right": 1}.get(direction, 0)
        nr, nc = r + dr, c + dc
        if 0 <= nr < gs.grid.rows and 0 <= nc < gs.grid.cols:
            self._selected = (nr, nc)
            self._render_and_display()

    def _advance_selection(self) -> None:
        gs = self._active
        if gs is None or self._selected is None:
            return
        r, c = self._selected
        rows, cols = gs.grid.rows, gs.grid.cols
        for _ in range(rows * cols):
            c += 1
            if c >= cols:
                c = 0
                r += 1
            if r >= rows:
                r = 0
            if gs.grid.cells[r][c].kind is not CellKind.BLOCK:
                self._selected = (r, c)
                return

    def _retreat_selection(self) -> None:
        gs = self._active
        if gs is None or self._selected is None:
            return
        r, c = self._selected
        rows, cols = gs.grid.rows, gs.grid.cols
        for _ in range(rows * cols):
            c -= 1
            if c < 0:
                c = cols - 1
                r -= 1
            if r < 0:
                r = rows - 1
            if gs.grid.cells[r][c].kind is not CellKind.BLOCK:
                self._selected = (r, c)
                return

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    def _add_annotation(self, display_x: float, display_y: float) -> None:
        text = tk.simpledialog.askstring("Add Text", "Enter text:", parent=self)
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
        r, c = self._selected
        cell = gs.grid.cells[r][c]
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
        result = tk.colorchooser.askcolor(
            color=f"#{r:02x}{g:02x}{b:02x}",
            title="Pick highlight colour",
        )
        if result[0] is None:
            return
        rgb = result[0]
        self._highlight_color = (int(rgb[2]), int(rgb[1]), int(rgb[0]))

    def _recompute_base(self) -> None:
        self._base_image = self._compute_base_image(
            self._image,
            self._grid_states,
            self._highlight_confidence,
        )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save_image(self) -> None:
        path = self._out_path
        if path is None:
            path = tk.filedialog.asksaveasfilename(
                defaultextension=".png",
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
        self.title(f"Crossword Grid Editor — saved {os.path.basename(str(path))}")

    def _save_csv(self) -> None:
        gs = self._active
        if gs is None:
            return
        path = tk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        gs.grid.save_csv(path)
        self.title(f"Crossword Grid Editor — saved {os.path.basename(path)}")

    def _on_close(self) -> None:
        self.destroy()
