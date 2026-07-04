# CLAUDE.md

Guidance for working in this repo.

## What this is

A Python library and interactive editor for detecting a crossword grid's layout
(blocked or barred) from a scanned image and letting a person fill it in by hand —
click a cell, type letters, highlight cells, add free-text annotations — then save
the result as an image or CSV. Public API: `edit_grid()` in `crossword_transcriber`.
There is no automatic letter recognition; all cell content is entered manually.

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

- **`src/` layout**, package `crossword_transcriber`. Pipeline is one module per
  stage: `preprocess` → `detection` → `segmentation` → `editor`.
- **Images are BGR `numpy` arrays** (OpenCV-native) everywhere. `io.load_image`
  also accepts an already-loaded array.
- Tests use a **synthetic grid generator** (`tests/synthetic.py`) for fast unit
  tests; **real scanned fixtures** live in `tests/fixtures/` with exact expected
  dimensions in `tests/test_fixtures.py`.

## Working cadence (important)

Implement **one phase at a time**. Before committing a phase, `ruff format` +
`ruff check` + `mypy src` + `pytest` must all be green. Commit each phase as its
own commit; end commit messages with the
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer. Confirm before
moving to the next phase.

## Scope (v1)

Clean scans; square uniform grids; **both blocked and barred** styles (never rely
on black blocks existing — detection is driven off the line lattice, present in
both); fully **offline**. Cells hold a single uppercase A–Z by default; the editor
also supports multi-letter cells (double-click) for barred grids that need them.

## Gotchas / notes for grid detection

- **Bold straight letter strokes can survive the morphological line extraction**
  in `detection.extract_line_mask` (long horizontal/vertical openings). This means
  you must segment cells from the grid lines, then crop each cell's **inner
  region** (excluding the border) before treating its contents as a letter —
  never re-detect a grid that already contains drawn/written letters.
- `detection.detect_grids` finds every quad whose area is within 10% of the
  largest line-mask contour, so a page can contain multiple grids; they're
  returned in reading order (top-to-bottom, left-to-right). `detect_grid` wraps
  this for the common single-grid case and raises `MultipleGridsError` if more
  than one is found and no `grid_index` is given.
- Handwriting that **crosses cell borders** (see `barred_very_messy.png`) can add
  streaks to the projection profile; segmentation handled it on that fixture, but
  it's the likely failure mode to watch when hardening.
