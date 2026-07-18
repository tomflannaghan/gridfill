# CLAUDE.md

Guidance for working in this repo.

## What this is

A Python library and CLI for detecting a crossword grid's layout (blocked or
barred) from a scanned image or PDF and saving it as a `.cwd` document (JSON:
base64 source image + grid state) — the empty grid, ready to be filled in.
PDF input uses the last page, rendered at 300 DPI (print quality at A4). Public
API: `detect_grids()` and `save_document()` in `gridfill`. There is no
automatic letter recognition; the document holds only the detected layout.

`editor.md` describes an interactive Tk editor that has been removed from the
codebase; it is kept only as a reference for a possible future front end.

## Dev environment & commands

Uses `uv` with a local `.venv`.

```bash
uv venv && uv pip install -e ".[dev]"   # core + dev tools
source .venv/bin/activate                # activate before running tools

pytest                                    # tests
ruff check src tests                      # lint
ruff format src tests                     # format (run before committing)
mypy src                                  # type check (strict)
```

## Conventions

Coordinates that get persisted to a `.cwd` document are always **normalized to
`[0, 1]`** as fractions of the source image width/height — never raw pixels.
This applies to both `Cell.polygon` vertices and text annotation `(x, y)`
positions, so a document stays valid independent of the image's resolution.
