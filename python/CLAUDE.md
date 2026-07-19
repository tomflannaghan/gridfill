# CLAUDE.md — Python library

Grid detection + `.cwd` I/O. See the repo root [CLAUDE.md](../CLAUDE.md) for
project-wide conventions (normalized coords, BGR colours, the mirrored `.cwd`
format). Run all tooling from this directory (`python/`).

The source is heavily docstring'd — read the module/function docstrings first;
this file is the map and the non-obvious invariants, not a restatement of them.

## The pipeline

CLI and API share one path (see [cli.py](src/gridfill/cli.py)):

```
load_image → to_grayscale → binarize → detect_grids → save_document
```

- [io.py](src/gridfill/io.py) — `load_image`. Images are **BGR numpy arrays**
  (OpenCV native) everywhere. A `.pdf` renders its **last page** at 300 DPI.
- [preprocess.py](src/gridfill/preprocess.py) — `binarize` produces an
  **inverted** binary image: **ink = 255, background = 0**. Every downstream CV
  stage assumes this polarity.
- [detection/](src/gridfill/detection/) — see below.
- [document.py](src/gridfill/document.py) — `.cwd` save/load. The rendered
  (filled-in) image is never stored; a document holds only the source image +
  grid state + annotations, enough to reconstruct everything.

## Two detectors, one combiner

`detect_grids` ([detection/combined.py](src/gridfill/detection/combined.py))
runs **both** detectors and merges:

- **Rectangular** ([rectangle.py](src/gridfill/detection/rectangle.py)) — the
  precise one. Isolates the axis-aligned **line lattice** (morphological opening
  with long 1-D kernels), finds grid quads, perspective-**rectifies** each, and
  projects cell boxes back to normalized source coords. Driven purely off grid
  *lines*, so it works for blocked and barred grids alike — it never relies on
  black blocks existing.
- **Irregular** ([irregular.py](src/gridfill/detection/irregular.py)) — the
  general one. Makes *no* shape assumption: labels the enclosed white regions,
  keeps the dominant same-size cluster, groups mutually-adjacent cells into
  lattices, and traces each cell polygon. Handles rhombi, hexagons, wedges.

Rectangular runs first and wins ties: a plain square grid reads as *both*, so
combined.py **drops any irregular grid that overlaps a rectangular one**
(bounding-box overlap > `_OVERLAP_FRACTION`). `GridDetectionError` is raised
only if *neither* detector finds anything.

Non-obvious bits worth knowing before you touch detection:

- **Two-pass line extraction (rectangular).** The coarse pass sizes its
  morphology kernel off the whole image, which erases the short borders of a
  single-row/column auxiliary grid. A second **fine** pass re-extracts with a
  kernel sized off the *reference* grid's cell pitch to recover those, then the
  masks are OR'd. Candidates whose cell pitch is off from the reference by
  > `_PITCH_TOLERANCE` are rejected (badges, logos, stray strokes).
- **`reading_order`** ([ordering.py](src/gridfill/detection/ordering.py)) is the
  *shared* top-to-bottom-then-left-to-right sort, used for cells within a grid
  *and* for whole grids on a page. It's band-based (a new row starts when `cy`
  jumps more than `band`), so the band parameter matters.

## Cell geometry: the incircle centre

Each `Cell` carries a `centre` (`polygon_centre` in
[geometry.py](src/gridfill/geometry.py)) — the **incircle** centre (largest
inscribed circle), *not* the vertex mean. For an irregular/concave cell the
vertex mean can drift or fall outside the shape; the incircle centre is where a
glyph actually sits and what navigation treats as the cell's location. It's
computed once at detection time and **persisted** in the `.cwd` so the web
editor never recomputes the distance transform.

## Types & serialization

- `Grid` is an ABC; concrete subclasses (`RectangularGrid`, `IrregularGrid`)
  self-register via `@register_grid_type("...")` so `grid_from_dict` can
  dispatch on the `"type"` key. **Add a new grid type by registering it** — the
  loader needs no other change.
- A `Cell` has no row/col of its own; its position is purely its index in the
  owning grid's flat `cells` list (row-major for rectangular).
- Errors form a hierarchy under `GridfillError`
  ([errors.py](src/gridfill/errors.py)); the CLI catches `GridfillError | OSError`.

## Testing

`pytest` from `python/`. Two flavours:

- **Synthetic** ([tests/synthetic.py](tests/synthetic.py)) — `make_grid` renders
  clean grids with known ground-truth geometry (plus optional title/clue clutter
  to prove detection ignores non-grid ink). Use for exact geometry assertions.
- **Real fixtures** ([tests/fixtures/](tests/fixtures/)) — genuine scans
  (barred, messy, multi-grid, irregular). Regression guards on real-world noise;
  ground-truth dims were confirmed by inspecting rectified output. When adding a
  fixture, assert only what you've verified from the actual image.
