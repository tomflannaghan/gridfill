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

The source image fills a canvas that resizes with the window (maintaining aspect ratio).

The letters that have been entered, highlighting, and annotations are rendered on top of the background image.

The grid that is currently selected should be highlighted with a green border.

### Zoom to grid

By default, selecting a cell **zooms the view to fit that cell's grid**, so the
whole image is only shown when nothing is selected. This is a view preference
toggled by the **Zoom to grid** checkbox in the top bar (on by default); with it
off, the view always fits the whole image. Moving the selection within a grid
keeps the same zoom; selecting a cell in another grid re-zooms to it, and
deselecting zooms back out.

## Tools

A **tool palette** on the left chooses what the pointer does. The **Select** tool
(the default) is for filling in the grid — everything under *Selecting and editing
cells* below applies to it. The **Text**, **Line** and **Curve** tools add
annotations, and the **Eraser** deletes them. See *Annotations* below.

## Selecting and editing cells

*(Select tool.)*

- **Click** a cell to select it (and switch to its grid). Clicking empty space
  deselects.
- **Type a letter or digit** to fill the selected cell; the selection then
  **auto-advances** to the next cell in reading order.
- **Arrow keys** move the selection to the adjacent cell in that direction.
- **Backspace** clears the current letter or, if the cell is already empty,
  steps back to the previous cell and clears it (crossword-style deletion).
  **Delete** clears the selected cell without moving.
- **Escape** deselects.

### Selecting multiple cells

Several cells can be selected at once so a colour can be applied to all of them:

- **Shift+Arrow** extends the selection as it moves, adding exactly the cells the
  cursor visits.
- **Drag a rectangle** (press on the canvas and drag) selects every cell with a
  corner inside the rectangle; releasing without dragging is an ordinary click.

Selected cells are shown with a blue fill. A plain arrow key, a single click, or
typing collapses back to a single selection. The **paintbrush** buttons in the
top bar apply the current highlight or text colour to the whole selection (see
*Highlighting* and *Text colour*).

### Multi-letter cells

**Double-click** a cell to enter *multi-entry mode*, where several characters
can be typed into a single cell (for rebus or multi-letter answers). In this
mode letters accumulate instead of advancing, Backspace removes one character at
a time, and **Enter** or **Escape** exits the mode.

## Highlighting

**Ctrl+H** toggles a coloured background on the selected cell (yellow by
default); pressing it again removes the highlight. **Ctrl+Shift+H** opens a
colour picker to choose a different colour for subsequent highlights.

The **paintbrush** button beside the **Highlight** colour in the top bar applies
that colour as the background of every selected cell (or the single selected
cell). This is a single undoable step.

## Text colour

Letters and annotations are drawn in **black** by default. The **Text** colour
control in the top bar chooses the colour used for **subsequently** typed
letters and newly created annotations (text, lines and curves), so different
entries can be given different colours; existing content keeps the colour it was
created with. Each cell's and annotation's colour is saved in the `.cwd`
document.

The **paintbrush** button beside the **Text** colour recolours the letters of
every selected cell (or the single selected cell) with the current text colour —
a single undoable step. This is the way to change the colour of letters already
entered.

## Annotations

Annotations are free content drawn on top of the grid — text, lines and curves —
useful for clue numbers, notes, labels, or marking up the puzzle. Each tool
creates one kind:

- **Text** — click empty space to place free text and start typing; press
  **Enter** or click away to finish.
- **Line** — press and drag to draw a straight line; release to finish.
- **Curve** — click to place a series of points; the curve is drawn smoothly
  through them. **Double-click** or press **Enter** to finish, **Escape** to
  cancel.

All new annotations use the current **Text** colour.

### Editing annotations

With the **Select** tool:

- **Click** an annotation to select it; a dashed outline and control handles
  appear.
- **Drag** its body to move it, or drag a **handle** to reshape it (an endpoint
  of a line, an anchor of a curve).
- **Double-click** a text annotation to edit its text.
- With an annotation selected, **Delete** (or **Backspace**) removes it.

The **Eraser** tool deletes any annotation you click on.

## Undo and redo

**Undo (Ctrl+Z)** reverses the last change — a typed letter, a highlight, or any
annotation edit — and **Redo (Ctrl+Shift+Z**, or **Ctrl+Y)** reapplies it.

## Saving and exporting

- **Save (Ctrl+S)** writes a `.cwd` document containing the source image and all
  grid state and annotations, so work can be resumed later.
- **Export (Ctrl+Shift+S)** writes the finished, filled-in grid as a PNG,
  without any of the editing chrome.

There is **no automatic letter recognition** — every cell's content is entered
by hand.
