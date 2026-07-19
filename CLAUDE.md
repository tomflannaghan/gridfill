# CLAUDE.md

Guidance for working in this repo.

## Repo layout

This is a monorepo:

- [python/](python/) — the Python library + CLI (grid detection, `.cwd` I/O).
  The Python project root: `pyproject.toml`, `src/gridfill/`, `tests/` all live
  here. Run all Python tooling from `python/`.
- [web/](web/) — the React + TypeScript frontend for editing `.cwd` documents
  in the browser (purely frontend, no backend). See [web/editor.md](web/editor.md)
  for the editor's intended behavior.
- A backend serving the frontend from the Python library is planned but not yet
  present.

## What this is

A Python library and CLI for detecting a crossword grid's layout (blocked or
barred) from a scanned image or PDF and saving it as a `.cwd` document (JSON:
base64 source image + grid state) — the empty grid, ready to be filled in.
PDF input uses the last page, rendered at 300 DPI (print quality at A4). Public
API: `detect_grids()` and `save_document()` in `gridfill`. There is no
automatic letter recognition; the document holds only the detected layout.

## Dev environment & commands

The Python project uses `uv` with a local `.venv`, from `python/`:

```bash
cd python
uv venv && uv pip install -e ".[dev]"   # core + dev tools
source .venv/bin/activate                # activate before running tools

pytest                                    # tests
ruff check src tests                      # lint
ruff format src tests                     # format (run before committing)
mypy src                                  # type check (strict)
```

The frontend uses `npm` from `web/` (`npm install`, `npm run dev`, `npm test`).

## Conventions

**Normalized coordinates.** Coordinates that get persisted to a `.cwd` document
are always **normalized to `[0, 1]`** as fractions of the source image
width/height — never raw pixels. This applies to both `Cell.polygon` vertices
and text annotation `(x, y)` positions, so a document stays valid independent of
the image's resolution.

**Colours are BGR.** Every colour that touches a `.cwd` document — cell
`background`, cell `text_colour`, annotation `colour` — is an OpenCV **BGR**
integer triple, not RGB. The default (black / no colour) is persisted as `null`.
On the web side the BGR↔RGB swap lives in exactly one place
([web/src/model/colour.ts](web/src/model/colour.ts)); don't scatter it.

**British spelling** in identifiers and prose (`centre`, `colour`, `neighbour`)
throughout — **including every `.cwd` format key and its TypeScript/Python
mirror** (`text_colour`/`textColour`, `colour`, never `text_color`/`textColor`/
`color`). The only exceptions are spellings a browser API mandates verbatim —
the DOM `<input type="color">` attribute, the CSS `color` property, the
`currentColor` SVG/CSS keyword — which of course can't be renamed. When adding
a persisted field, spell its key (and any in-memory field mirroring it) the
British way on both sides.

## The `.cwd` format is mirrored in two languages

The document format is defined **twice** and the two must stay byte-compatible:

- Python: [python/src/gridfill/document.py](python/src/gridfill/document.py) +
  [types.py](python/src/gridfill/types.py) (`save_document` / `load_document`).
- TypeScript: [web/src/model/cwd.ts](web/src/model/cwd.ts) (`parseCwd` /
  `serializeCwd`).

A `.cwd` file is plain JSON (base64 PNG + grids + annotations), so the web
editor needs no backend to read or write one. **Any change to the on-disk shape
must be made in both files**, including the `format` magic and the
`_LEGACY_FORMAT_MAGICS` / `LEGACY_FORMAT_MAGICS` set (the project was renamed
`crossword-transcriber` → `inkwell` → `gridfill`, and old documents still load).
