# CLAUDE.md

Guidance for working in this repo.

## Repo layout

This is a monorepo:

- [python/](python/) — the Python library + CLI (grid detection, `.cwd` I/O),
  plus an optional HTTP backend ([server.py](python/src/gridfill/server.py),
  `gridfill-server`) that lets the web editor upload a scan and get a detected
  `.cwd` back. The Python project root: `pyproject.toml`, `src/gridfill/`,
  `tests/` all live here. Run all Python tooling from `python/`.
- [web/](web/) — the React + TypeScript frontend for editing `.cwd` documents
  in the browser. It needs no backend to open/save/export a `.cwd` file (it's
  plain JSON) — the backend above is only used to go from a raw scan to one.
  See [web/editor.md](web/editor.md) for the editor's intended behavior.

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

**Pixel coordinates.** Coordinates that get persisted to a `.cwd` document are
always **source-image pixel positions** — never normalized fractions. This
applies to `Cell.polygon` vertices, `Cell.centre` / `Cell.size` (the incircle
centre and diameter), and text/line/curve annotation coordinates. Pixels were
chosen over `[0, 1]` fractions because a *length* (like `Cell.size`) has no
inherent x or y axis to be "a fraction of" — the source image's width and
height generally differ, so there's no single, unambiguous way to normalize a
scalar against them. Pixels sidestep that: every coordinate and every length
uses the same unit, so the web viewport's image-to-canvas map is a single
uniform scale (`web/src/canvas/viewport.ts`), not two different formulas for
points versus lengths.

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

A `version` integer (`_FORMAT_VERSION` in `document.py`, `FORMAT_VERSION` in
`cwd.ts`) is also written and checked on load; both sides reject a document
whose `version` doesn't match rather than silently misinterpreting it. Bump it
on any change where an old document would parse but mean something different
(e.g. version 2 switched coordinates from normalized `[0, 1]` to pixels) — not
for an additive, always-optional field like `Cell.text_colour`, which old
documents simply lack and both loaders already default.
