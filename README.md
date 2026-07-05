# gridfill

Detect a crossword grid's layout from a scanned image or PDF and
edit it interactively: click a cell, type letters, highlight cells, drop
free-text annotations, then save your progress as a `.cwd` document or export
the result as an image.

## Install (development)

```bash
uv venv
uv pip install -e ".[dev]"
```

## Standalone executable

No Python install needed for end users. Prebuilt Windows and Linux
executables are attached to each [release](../../releases) (built by
[.github/workflows/build.yml](.github/workflows/build.yml) via PyInstaller).
Double-click, or drag a scan/PDF/`.cwd` file onto the executable to open it
directly.

To build one yourself:

```bash
uv sync --extra build
uv run pyinstaller --noconfirm --clean packaging/gridfill.spec
# -> dist/gridfill(.exe)
```

PyInstaller doesn't cross-compile, so this produces an executable for
whichever OS you run it on; the release workflow builds both by running on
GitHub-hosted Linux and Windows runners.

### App icon

[src/gridfill/assets/icon.svg](src/gridfill/assets/icon.svg) is the source of
truth. `icon.png` (the Tk window/taskbar icon, loaded at runtime) and
`packaging/icon.ico` (the Windows `.exe` icon, embedded at build time) are
generated from it and checked in, so if you edit the SVG, regenerate both:

```bash
inkscape --export-type=png --export-filename=/tmp/icon_256.png \
    -w 256 -h 256 src/gridfill/assets/icon.svg

python3 -c "
from PIL import Image
img = Image.open('/tmp/icon_256.png').convert('RGBA')
img.save('src/gridfill/assets/icon.png')
img.save('packaging/icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
"
```

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

```python
from gridfill import edit_grid

# Opens an interactive editor window for every grid found in the image.
# Also accepts a PDF (its last page is rendered at print resolution), the
# path to a .cwd document to resume a previous session, or no source at all
# to start blank (use File > Open in the editor).
# Returns the edited RectangularGrid objects when the window is closed.
grids = edit_grid("scan.png", out_path="filled_out.png")
```

In the editor: click a cell to select it and type a letter; double-click for
multi-letter cells (barred grids). `Ctrl+O` opens an image, PDF, or `.cwd`
document; `Ctrl+S` saves your progress to a `.cwd` document (the source image
plus all grid state, so you can reopen and keep editing); `Ctrl+Shift+S`
exports the rendered image. See the menu bar for highlighting and free-text
annotation tools.

## Development

```bash
ruff check . && ruff format --check .
mypy src
pytest
```
