# gridfill

Detect a crossword grid's layout from a scanned image or PDF and
edit it interactively: click a cell, type letters, highlight cells, drop
free-text annotations, then save your progress as a `.cwd` document or export
the result as an image.

## Standalone executable

No Python install needed. Prebuilt Windows and Linux executables are attached
to each [release](../../releases). Double-click, or drag a scan/PDF/`.cwd`
file onto the executable to open it directly.

## Usage

```bash
gridfill scan.png -o filled_out.png
# A PDF also works; its last page is used:
gridfill scan.pdf
# Or resume a session saved earlier:
gridfill scan.cwd
# Or start blank and use File > Open:
gridfill
```

In the editor: click a cell to select it and type a letter; double-click for
multi-letter cells (barred grids). `Ctrl+O` opens an image, PDF, or `.cwd`
document; `Ctrl+S` saves your progress to a `.cwd` document (the source image
plus all grid state, so you can reopen and keep editing); `Ctrl+Shift+S`
exports the rendered image. See the menu bar for highlighting and free-text
annotation tools.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for installing from source, using the
Python API, building the executable, and running tests.
