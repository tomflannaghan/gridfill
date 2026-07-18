# The Gridfill Editor

The editor is the interactive front end of Gridfill — a Tk application
(`_GridEditor`) that displays a detected crossword grid overlaid on its source
image and lets a person fill it in by hand. It's launched via `edit_grid()` or
the `gridfill` CLI.

## Starting up and loading content

You can open the editor three ways, all routed through `_load_source`:

- **From an image** (PNG/JPG/BMP/TIFF) or **PDF** (its last page, rendered at
  300 DPI) — the image is binarized and run through grid detection, which finds
  one or more grids and classifies each cell as a block, empty cell, or letter
  cell.
- **From a `.cwd` document** — a JSON file previously saved by the editor,
  carrying the base64 source image plus all grid state and text annotations.
  This resumes a session exactly where it was left.
- **With nothing** — a blank grey canvas showing a placeholder icon, from which
  you use **File → Open** to load any of the above.

The detected grids can be **rectangular** (a regular row/column lattice) or
**irregular** (arbitrarily-shaped cells — rhombi, hexagons, wedges — forming a
continuous lattice). The editor treats both uniformly through a flat,
reading-ordered list of cells; only navigation cares about the geometry.

## The display

The source image is shown on a resizable canvas with the grid composited on top
of it. To stay responsive, the editor keeps two resolutions in play
(`_refit_display`): a **downscaled display copy** fitted to the current window,
redrawn on every keystroke, and the **untouched full-resolution image** used
only when exporting or saving. Fonts are fitted twice to match — sized to each
grid's cells via the incircle of the first cell. Resizing the window (debounced)
refits everything so the view always fills the available space. When multiple
grids are present, the **active grid is indicated** visually, and letterboxing
fills any leftover canvas space.

## Selecting and editing cells

- **Click** a cell to select it (and make its grid active). Clicking a block
  just activates that grid without selecting. Clicking empty space deselects.
- **Type a letter/digit** to fill the selected cell; it's marked as a letter
  cell and the selection **auto-advances** to the next non-block cell in reading
  order (no wrap past the end).
- **Arrow keys** move the selection to the geometrically adjacent cell. For
  rectangular grids that's a row/column step; for irregular grids it's a spatial
  search for the nearest cell within a 45° cone in that direction.
- **Backspace** clears the current letter or, if the cell is already empty,
  retreats to the previous cell and clears it (crossword-style deletion).
  **Delete** clears the selected cell outright.
- **Escape** deselects; **File/Save/Highlight** shortcuts (Ctrl+O/S/H, with
  Shift variants) are handled globally.

### Multi-letter cells

**Double-clicking** a cell enters *multi-entry mode*, where several characters
can be typed into a single cell (for rebus/multi-letter answers). In this mode
letters accumulate rather than advancing, Backspace peels off one character at a
time, and **Enter** or **Escape** exits the mode.

## Highlighting

**Ctrl+H** toggles a colored background on the selected cell (default yellow);
toggling again removes it. **Ctrl+Shift+H** opens a color picker to choose a
different highlight color for subsequent cells. Highlights are baked into the
cached base image so they persist visually and are saved with the document.

## Text annotations

**Double-clicking empty space** (outside any grid) prompts for free text and
drops it at that spot as an annotation — useful for clue numbers, notes, or
labels. Annotation positions are stored **normalized to `[0,1]`** of the source
image, so they stay valid at any resolution. **Text → Clear All Text** removes
them.

## Saving and exporting

- **Save (Ctrl+S)** writes a `.cwd` document — the embedded source image plus
  every grid's cells (kind, letters, highlight colors) and all annotations — so
  work can be resumed later. If no path is set yet, it prompts, defaulting to
  the input's basename.
- **Export Image (Ctrl+Shift+S)** renders the filled grid at full resolution
  onto the original image and writes a PNG/JPEG. The export render drops
  interactive chrome — no blank-state icon, active-grid indicator, or selection
  outline — producing a clean finished picture.

There is **no automatic letter recognition** — every cell's content is entered
by hand.
