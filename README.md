# crossword-transcriber

Detect a handwritten crossword grid's layout from a scanned image and edit it
interactively: click a cell, type letters, highlight cells, drop free-text
annotations, then save the result as an image or CSV.

## Install (development)

```bash
uv venv
uv pip install -e ".[dev]"
```

## Usage

```bash
crossword-transcriber edit scan.png -o filled_out.png
```

```python
from crossword_transcriber import edit_grid

# Opens an interactive editor window for every grid found in the image.
# Returns the edited RectangularGrid objects when the window is closed.
grids = edit_grid("scan.png", out_path="filled_out.png")
```

In the editor: click a cell to select it and type a letter; double-click for
multi-letter cells (barred grids). `Ctrl+S` saves the rendered image, `Ctrl+Shift+S`
saves the active grid as CSV. See the menu bar for highlighting and free-text
annotation tools.

## Scope (v1)

Clean scans; square uniform grids (blocked **and** barred); fully offline.

## Development

```bash
ruff check . && ruff format --check .
mypy src
pytest
```
