# Crossword Grid Transcriber — Project Plan

## 1. Overview

A Python library to transcribe handwritten crossword grids to and from images.

It has two core capabilities:

1. **Read** — Given a photo/scan of a *filled* crossword grid, detect the grid on
   the page, segment it into cells, and recognise the handwritten letter (if any)
   in each cell. Output: a 2D array of letters.
2. **Write** — Given an image of an *empty* crossword grid and a 2D array of
   letters, render the letters into the appropriate cells at a sensible font size
   and output a new image of the filled grid.

The two stages share a common foundation: **grid detection and cell
segmentation**. Build this once and reuse it for both reading and writing.

## 1a. Confirmed scope (v1)

- **Inputs are clean scans.** Phone photos (shadows, perspective, noise) are a
  later concern — v1 can assume well-lit, roughly axis-aligned scans. We still do
  light deskew but can defer heavy perspective/illumination robustness.
- **Grids are always square and uniform** (equal-sized square cells, a known/
  inferable N×N lattice).
- **Two grid styles must both work:** *blocked* (black-square crosswords) and
  *barred* (no black cells — word boundaries marked by thick bars on cell edges).
  **Do not rely on black blocks existing.** Treat block detection as optional, and
  make the default assumption "every cell is a letter cell." For barred grids we
  do **not** need to detect the bars at all to transcribe letters — every cell is
  read independently.
- **Letters are single uppercase A–Z only.** No digits, no rebus/multi-letter
  cells. The classifier output space is exactly 26 classes.
- **Offline only.** No cloud APIs. HCR must run locally (rules out cloud Vision;
  EMNIST CNN is the primary plan, with TrOCR as an optional local upgrade).
- **Output is a list of lists** (`list[list[str | None]]`), `None` for a block
  cell, `""` (or `None`) for an empty white cell, otherwise the uppercase letter.

## 2. Problem breakdown

### 2.1 Reading pipeline

```
image ──▶ preprocess ──▶ detect grid ──▶ rectify (deskew/warp)
      ──▶ segment cells ──▶ classify cell (block / empty / letter)
      ──▶ recognise letter ──▶ assemble 2D array
```

Sub-problems and the hard parts:

- **Preprocessing** — grayscale, denoise, adaptive threshold, correct
  illumination. Photos (vs. clean scans) have shadows, perspective, and uneven
  lighting; this is where most robustness is won or lost.
- **Grid detection** — the page may contain clues, titles, and other content. We
  need to locate the grid region specifically (a dense, regular lattice of
  squares) and ignore everything else.
- **Rectification** — correct for perspective/rotation so cells map to an axis-
  aligned grid. A 4-point perspective transform onto the grid's bounding quad.
- **Cell segmentation** — determine the grid's dimensions (rows × cols) and the
  pixel bounds of every cell. Crossword grids are uniform, so once we know the
  outer rectangle and the line spacing we can divide it evenly.
- **Cell classification** — each cell is one of: **block** (filled black square,
  not part of the answer), **empty white cell**, or **white cell containing a
  handwritten letter**. Also detect/ignore small printed clue-number digits in
  cell corners.
- **Handwriting recognition (HCR)** — classify the single handwritten character.
  Crosswords are heavily constrained: typically a *single uppercase A–Z letter*
  per cell. This is far easier than general handwriting OCR.

### 2.2 Writing pipeline

```
empty grid image + letters ──▶ detect grid ──▶ segment cells
                           ──▶ for each cell, render centred letter
                           ──▶ composite onto image ──▶ output
```

Sub-problems:

- Reuse grid detection + cell segmentation from the read pipeline.
- For each letter, choose a font size that fits the cell with margin, centre it,
  and draw it (default: clean printed font; optional handwriting-style font).
- Composite text onto a copy of the original image (preserve the original).

## 3. Technical approach

### 3.1 Grid detection (shared)

Candidate strategy (start simple, escalate only if needed):

1. **Threshold + morphology to isolate grid lines.** Adaptive threshold, then use
   morphological operations with long horizontal and vertical kernels to extract
   horizontal and vertical line masks separately. Their intersection gives line
   crossings; their union gives the grid skeleton.
2. **Find the grid bounding box.** The largest connected component / contour of
   the combined line mask that is approximately square and "grid-like" (high line
   density) is the crossword. Use `cv2.findContours` + `approxPolyDP` to get a
   4-point quad.
3. **Rectify** with `cv2.getPerspectiveTransform` + `cv2.warpPerspective`.
4. **Infer rows/cols.** Project the rectified line mask onto the X and Y axes; the
   peaks in each projection are grid lines. Count gaps to get cols/rows and the
   precise cell boundaries. (Robust to slightly uneven cells.)

Fallback / alternative: Hough line transform (`cv2.HoughLinesP`) to find the line
grid directly. Keep the projection method as the primary approach — it's more
robust for clean lattices.

### 3.2 Cell classification (read)

For each segmented cell (with a small inner margin to drop the border lines):

- **Block detection (optional)** — mean pixel intensity below a threshold (mostly
  black) ⇒ block cell, emit `None`. **Barred grids have no blocks**, so this must
  never be required: the default is "treat as a letter cell." Only blocked grids
  trigger this branch, and the check is cheap, so we can always run it safely — a
  barred grid simply never matches.
- **Empty vs. filled** — ink coverage (fraction of dark pixels after
  thresholding) below a small threshold ⇒ empty cell.
- **Bars are ignored.** In barred grids the thick edge lines are part of the cell
  border region; the inner-margin crop already drops border pixels, so bars don't
  interfere with letter recognition. We do not need to detect them for v1.
- **Clue numbers** — small printed digits in a corner; ignore by masking the
  cell's corner region, or by size/position heuristics, before HCR.

### 3.3 Handwriting recognition (read)

Decision: treat this as **single-character classification** over exactly **26
classes (uppercase A–Z)**, not sequence OCR. **Must run offline.**

Options, in rough order of preference (cloud options excluded — offline-only):

| Option | Pros | Cons |
|---|---|---|
| **CNN trained on EMNIST (letters split)** | Purpose-built for single chars, small, fast, fully offline, easy to fine-tune on our own samples | Need a training step; EMNIST style differs from real users |
| **TrOCR (handwritten) via `transformers`** | Strong accuracy; runs locally (offline) | Heavy dependency, slower, overkill for single chars |
| **Tesseract (`pytesseract`)** | Offline, trivial to set up | Poor on handwriting; really for print |

**Plan:** Start with an EMNIST-trained CNN restricted to uppercase A–Z behind a
clean `LetterClassifier` interface. Keep the interface model-agnostic so a local
TrOCR backend can be swapped in later without touching the pipeline. Constrain
outputs to the 26 letters. Optionally collect misclassified real samples to
fine-tune. (EMNIST has lowercase/uppercase splits; map to uppercase since inputs
are uppercase only — this also lets us fold case-confusable pairs like c/C, o/O.)

Confidence handling: return a per-cell confidence so the caller can flag low-
confidence cells for human review.

### 3.4 Writing letters (write)

- Use **Pillow** (`ImageDraw` + `ImageFont`).
- Pick font size by measuring glyph bounds (`font.getbbox`) and scaling to fit the
  cell minus a margin (e.g. target ~60–70% of cell height).
- Centre using the measured text bbox (account for font ascent/descent).
- Provide a configurable font path; ship a default. Optionally support a
  handwriting-style TTF for a natural look.

## 4. Recommended libraries

Core:
- **opencv-python** — image processing, grid detection, perspective transforms.
- **numpy** — array representation and pixel math.
- **Pillow** — drawing text into cells (write stage), basic image I/O.
- **scikit-image** — handy supplementary CV ops (optional but useful).

HCR (one of):
- **torch** + **torchvision** — EMNIST dataset + a small CNN (primary plan).
- *or* **transformers** — TrOCR backend (alternative/upgrade path).
- **pytesseract** — only if a print-OCR fallback is wanted.

Tooling / quality:
- **pytest** — tests.
- **ruff** — lint + format.
- **mypy** — type checking.
- **pydantic** *(optional)* — typed config objects.

## 5. Project structure

```
transcriber/
├── pyproject.toml              # build config, deps, tool settings (ruff/mypy/pytest)
├── README.md
├── PLAN.md                     # this file
├── src/
│   └── crossword_transcriber/
│       ├── __init__.py         # public API: read_grid(), write_grid()
│       ├── types.py            # Grid, Cell, CellKind, BoundingBox dataclasses
│       ├── io.py               # load/save images
│       ├── preprocess.py       # grayscale, threshold, denoise, illumination
│       ├── detection.py        # grid detection + perspective rectification
│       ├── segmentation.py     # rows/cols inference + per-cell bounds
│       ├── classify.py         # block / empty / letter cell classification
│       ├── recognize/
│       │   ├── __init__.py     # LetterClassifier interface (protocol)
│       │   ├── cnn.py          # EMNIST CNN backend
│       │   └── trocr.py        # optional TrOCR backend
│       ├── reader.py           # orchestrates the read pipeline
│       ├── writer.py           # orchestrates the write pipeline
│       └── debug.py            # visualisation overlays for each stage
├── models/                     # trained weights (gitignored or via LFS)
├── scripts/
│   ├── train_cnn.py            # train the EMNIST letter classifier
│   └── demo.py                 # end-to-end CLI demo
├── tests/
│   ├── fixtures/               # sample grid images + expected arrays
│   ├── test_detection.py
│   ├── test_segmentation.py
│   ├── test_classify.py
│   ├── test_recognize.py
│   ├── test_reader.py
│   └── test_writer.py
└── docs/
    └── pipeline.md
```

### Public API sketch

```python
from crossword_transcriber import read_grid, write_grid

# Read: scan path/array -> list[list[str | None]]
#   None = block cell, "" = empty white cell, "A".."Z" = recognised letter
grid = read_grid("filled.png")

# Write: empty grid image + letters -> filled image
write_grid("empty.jpg", grid, out_path="filled_out.png")
```

### Core data types

- `CellKind` — enum: `BLOCK`, `EMPTY`, `LETTER`. (`BLOCK` only occurs in blocked
  grids; barred grids use only `EMPTY`/`LETTER`.)
- `Cell` — kind, bounding box (in rectified coords), letter, confidence.
- `Grid` — rows, cols, `list[list[Cell]]`, plus the rectification transform so the
  same geometry can be reused for writing.

## 6. Testing strategy

- **Unit tests** per stage using small synthetic fixtures (generate clean grids
  programmatically so tests don't depend on real photos).
- **Synthetic data generator** — render grids with known letters (reuse the write
  pipeline) to create labelled read-pipeline test cases. Add controlled
  perturbations (rotation, perspective, noise, blur) to test robustness.
- **Golden tests** — a handful of real photos in `tests/fixtures/` with hand-
  labelled expected arrays; assert accuracy ≥ a threshold (allow some tolerance).
- **Round-trip test** — `write_grid` then `read_grid` should recover the letters
  (using a clean printed font where HCR should be near-perfect).
- **Debug visualisations** — `debug.py` draws detected grid lines, cell bounds,
  and predicted letters over the source image for manual inspection.

## 7. Phased implementation

1. **Phase 0 — Scaffold.** `pyproject.toml`, package skeleton, CI/lint/test setup,
   data types, image I/O.
2. **Phase 1 — Grid geometry.** Preprocess → detect → rectify → segment. Validate
   with the debug overlay on synthetic + real images. *This is the backbone for
   both pipelines.*
3. **Phase 2 — Write pipeline.** Render letters into segmented cells. Easy to
   verify visually and gives us a synthetic-data generator for Phase 4.
4. **Phase 3 — Cell classification.** Block / empty / letter; ignore clue numbers.
5. **Phase 4 — Letter recognition.** Train EMNIST CNN behind `LetterClassifier`;
   integrate; add confidence + low-confidence flagging.
6. **Phase 5 — End-to-end + hardening.** Full read pipeline, round-trip tests,
   robustness to photos (lighting/perspective), accuracy tuning, optional TrOCR
   backend.

## 8. Key risks & mitigations

- **HCR accuracy gap (EMNIST vs. real handwriting)** — now the biggest risk, since
  scans remove most CV difficulty. Keep the classifier pluggable; collect real
  misclassifications to fine-tune; surface per-cell confidence so a human can
  correct the few hard cells.
- **Barred grids have no blocks to anchor detection** — don't rely on block cells
  for finding/segmenting the grid; drive detection purely off the line lattice,
  which is present in both styles. Bars are thicker lines but still part of the
  lattice, so projection-based segmentation still works.
- **Grid detection failing on cluttered pages** — use grid-density heuristics to
  pick the lattice; expose a manual ROI/crop override as an escape hatch.
- **Clue numbers misread as letters** — mask cell corners before HCR; classify by
  size/position.
- **Phone photos (deferred)** — perspective/illumination robustness is out of
  scope for v1 but the pipeline keeps a rectification stage so we can strengthen
  it later without restructuring.

## 9. Resolved scope decisions

All initial open questions are now answered — see **§1a Confirmed scope**:
- Inputs: **clean scans** for v1 (phone photos later).
- Grids: **square, uniform**; both **blocked and barred** styles; no reliance on
  black blocks.
- Letters: **uppercase A–Z only**, single letter per cell.
- **Offline only** — no cloud HCR.
- Output: **list of lists** (`None` block / `""` empty / `"A".."Z"`).
