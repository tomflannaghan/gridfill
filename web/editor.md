# The Gridfill Editor

The editor is an interactive front end for Gridfill: it displays a detected
crossword grid overlaid on its source image and lets a person fill it in by
hand.

## Starting up and loading content

You can open the editor with:

- **A `.cwd` document** — a file saved by a previous session, which resumes work
  exactly where it was left off, with all grid state and text annotations
  intact.
- **Nothing** — a blank canvas, from which you use **File → Open** to load any of
  the above.

Grids can be **rectangular** (a regular row/column layout) or **irregular**
(arbitrarily-shaped cells — rhombi, hexagons, wedges). Both are filled in the
same way; only how the arrow keys move between cells differs.

## The display

The source image fills a resizable canvas with the grid drawn on top of it.
Resizing the window reflows the view so it always fills the available space.
When a puzzle contains more than one grid, the one you're currently working in
is highlighted.

## Selecting and editing cells

- **Click** a cell to select it (and switch to its grid). Clicking empty space
  deselects.
- **Type a letter or digit** to fill the selected cell; the selection then
  **auto-advances** to the next cell in reading order.
- **Arrow keys** move the selection to the adjacent cell in that direction.
- **Backspace** clears the current letter or, if the cell is already empty,
  steps back to the previous cell and clears it (crossword-style deletion).
  **Delete** clears the selected cell without moving.
- **Escape** deselects.

### Multi-letter cells

**Double-click** a cell to enter *multi-entry mode*, where several characters
can be typed into a single cell (for rebus or multi-letter answers). In this
mode letters accumulate instead of advancing, Backspace removes one character at
a time, and **Enter** or **Escape** exits the mode.

## Highlighting

**Ctrl+H** toggles a colored background on the selected cell (yellow by
default); pressing it again removes the highlight. **Ctrl+Shift+H** opens a
color picker to choose a different color for subsequent highlights.

## Text annotations

**Double-click empty space** (outside any grid) to add free text at that spot —
useful for clue numbers, notes, or labels. **Text → Clear All Text** removes
all annotations.

## Saving and exporting

- **Save (Ctrl+S)** writes a `.cwd` document containing the source image and all
  grid state and annotations, so work can be resumed later.
- **Export Image (Ctrl+Shift+S)** writes the finished, filled-in grid as a
  PNG or JPEG, without any of the editing chrome.

There is **no automatic letter recognition** — every cell's content is entered
by hand.
