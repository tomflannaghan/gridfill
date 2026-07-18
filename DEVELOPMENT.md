# Development

See [README.md](README.md) for what gridfill is and how to use it. This
document covers installing from source, the Python API, building the
standalone executable, and running checks.

The Python project lives in [python/](python/); run all commands below from
there.

## Install

```bash
cd python
uv venv
uv pip install -e ".[dev]"
```

## Standalone executable

Prebuilt Windows, macOS, and Linux executables are attached to each
[release](../../releases), built by
[.github/workflows/build.yml](.github/workflows/build.yml) via PyInstaller.

To build one yourself (from `python/`):

```bash
uv sync --extra build
uv run pyinstaller --noconfirm --clean packaging/gridfill.spec
# -> python/dist/gridfill(.exe)
```

PyInstaller doesn't cross-compile, so this produces an executable for
whichever OS you run it on; the release workflow builds all three by running
on GitHub-hosted Linux, Windows, and macOS runners. The macOS runner is
Apple Silicon, so that build is arm64-only.

### App icon

[python/src/gridfill/assets/icon.svg](python/src/gridfill/assets/icon.svg) is the
source of truth. `python/packaging/icon.ico` (the Windows `.exe` icon, embedded
at build time) is generated from it and checked in, so if you edit the SVG,
regenerate it:

```bash
inkscape --export-type=png --export-filename=/tmp/icon_256.png \
    -w 256 -h 256 src/gridfill/assets/icon.svg

python3 -c "
from PIL import Image
img = Image.open('/tmp/icon_256.png').convert('RGBA')
img.save('packaging/icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
"
```

## Checks

```bash
ruff check . && ruff format --check .
mypy src
pytest
```
