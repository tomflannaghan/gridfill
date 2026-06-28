# CLAUDE.md

Guidance for working in this repo. See [PLAN.md](PLAN.md) for the full design and
phased roadmap.

## What this is

A Python library to **read** handwritten crossword grids from images into a 2D
letter array, and **write** a letter array back into an empty grid image. Public
API: `read_grid()` / `write_grid()` in `crossword_transcriber`.

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

Heavy ML deps (torch/torchvision/onnx) live in the optional `[train]` extra so the
core installs without a deep-learning toolchain. Runtime inference uses `cv2.dnn`
with no torch dependency.

## Conventions

- **`src/` layout**, package `crossword_transcriber`. Pipeline is one module per
  stage: `preprocess` → `detection` → `segmentation` → `classify` → `recognize/`
  → `reader`/`writer`.
- **Images are BGR `numpy` arrays** (OpenCV-native) everywhere. `io.load_image`
  also accepts an already-loaded array.
- **Recognition is decoupled** behind the `LetterClassifier` Protocol in
  `recognize/__init__.py`; the pipeline never imports a concrete backend.
- Unbuilt pipeline stages are stubs that `raise NotImplementedError("Phase N: …")`.
- Tests use a **synthetic grid generator** (`tests/synthetic.py`) for fast unit
  tests; **real scanned fixtures** live in `tests/fixtures/` with exact expected
  dimensions in `tests/test_fixtures.py`.

## Working cadence (important)

Implement **one phase at a time** (see PLAN.md §7). Before committing a phase,
`ruff format` + `ruff check` + `mypy src` + `pytest` must all be green. Commit each
phase as its own commit; end commit messages with the
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer. Confirm before
moving to the next phase.

## Scope (v1) — see also PLAN.md §1a

Clean scans; square uniform grids; **both blocked and barred** styles (never rely
on black blocks existing — detection is driven off the line lattice, present in
both); **single uppercase A–Z** per cell; fully **offline**. **Multi-letter cells
are out of scope** (`barred_multiletter_cells.png` is a detection-only fixture).
Output is `list[list[str | None]]`: `None` block / `""` empty / `"A".."Z"`.

## Gotchas / notes for the read pipeline (Phase 5)

- **Bold straight letter strokes can survive the morphological line extraction**
  in `detection.extract_line_mask` (long horizontal/vertical openings). This means
  you must segment cells from the grid lines, then crop each cell's **inner
  region** (excluding the border) before reading the letter — never re-detect a
  grid that already contains drawn/written letters.
- Detection currently picks the **largest line-mask contour** as the grid. This
  works on all real fixtures (clue text, titles, badges, external handwriting are
  all rejected), but assumes the grid is the dominant lattice on the page.
- Handwriting that **crosses cell borders** (see `barred_very_messy.png`) can add
  streaks to the projection profile; segmentation handled it on that fixture, but
  it's the likely failure mode to watch when hardening.
- **Cell cleanup pipeline** (`reader.py`): before recognition each cell goes through
  border line stripping → background normalization → corner clue removal. Corner
  clue removal uses connected components and must require the **full bounding box**
  to be contained in the corner region — checking only the origin point removes
  parts of letters that start in the corner but extend beyond it.
