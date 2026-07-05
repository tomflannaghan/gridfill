# Development

See [README.md](README.md) for what gridfill is and how to use it. This
document covers installing from source, the Python API, building the
standalone executable, and running checks.

## Install

```bash
uv venv
uv pip install -e ".[dev]"
```

## Standalone executable

Prebuilt Windows and Linux executables are attached to each
[release](../../releases), built by
[.github/workflows/build.yml](.github/workflows/build.yml) via PyInstaller.

To build one yourself:

```bash
UV_NO_MANAGED_PYTHON=1 uv sync --extra build
UV_NO_MANAGED_PYTHON=1 uv run pyinstaller --noconfirm --clean packaging/gridfill.spec
# -> dist/gridfill(.exe)
```

`UV_NO_MANAGED_PYTHON=1` forces uv to build against your system's Python
rather than downloading its own. On Linux this matters: uv's managed
(python-build-standalone) builds bundle a Tcl/Tk that PyInstaller can't
freeze cleanly, producing an executable that crashes on startup with
`undefined symbol: TclBN_mp_to_ubin`. Your system Python doesn't have this
problem, so long as it has tkinter available (`python3 -c "import tkinter"`;
install your distro's `python3-tkinter`/`python3-tk` package if that fails).

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

## Checks

```bash
ruff check . && ruff format --check .
mypy src
pytest
```
