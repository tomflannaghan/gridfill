---
name: debug-detection
description: Diagnose why gridfill grid detection gives a wrong or empty result on a specific image or .cwd. Use when detection returns the wrong rows/cols, misses a grid, finds spurious grids, or raises GridDetectionError — dumps the intermediate CV stages (binary, line mask, quads, cell boxes / labelled regions) as PNGs so the failing stage is visible.
---

# Debugging grid detection

Detection is a CV pipeline where failures are only understandable **visually** —
which stage first goes wrong tells you what to fix. Don't guess from the final
rows/cols; dump the stages.

## Pipeline recap (where things break)

```
load_image → to_grayscale → binarize(ink=255) → detect_grids → grids
                                                  ├── rectangular: extract_line_mask → find quads → rectify → infer_cell_boxes
                                                  └── irregular:   label enclosed regions → size-filter → adjacency groups → polygons
```

Common failure → likely stage:

- **Empty / GridDetectionError** — `binarize` polarity or contrast (is ink
  really 255?), or `extract_line_mask` kernel erasing short borders.
- **Wrong rows/cols** — `infer_cell_boxes` line-position detection (`min_value`
  threshold, `min_gap` merging thick/anti-aliased lines).
- **Spurious extra grid** — a badge/logo passing the pitch filter, or an
  irregular grid not being dropped as overlapping a rectangular one.
- **Missing auxiliary single-row/col grid** — the fine (pitch-sized) line pass,
  or the `_PITCH_TOLERANCE` reject.

## How to run

From `python/` with the venv active. Write this to the scratchpad and run it
with the target image (or a `.cwd` — its embedded PNG is decoded):

```python
# stagedump.py — usage: python stagedump.py <image-or-.cwd> [outdir]
import sys, base64, json, pathlib
import cv2, numpy as np
from gridfill.io import load_image
from gridfill.preprocess import to_grayscale, binarize
from gridfill.detection.rectangle import extract_line_mask, detect_rectangular_grids
from gridfill.detection.irregular import detect_irregular_grids
from gridfill.detection import detect_grids

src = sys.argv[1]
out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "stages"); out.mkdir(exist_ok=True)

if src.endswith(".cwd"):
    data = json.loads(pathlib.Path(src).read_text())
    buf = np.frombuffer(base64.b64decode(data["image"]["data"]), np.uint8)
    image = cv2.imdecode(buf, cv2.IMREAD_COLOR)
else:
    image = load_image(src)

gray = to_grayscale(image)
binary = binarize(gray)
cv2.imwrite(str(out / "1_binary.png"), binary)          # expect ink=white on black
cv2.imwrite(str(out / "2_linemask.png"), extract_line_mask(binary))  # only grid lines survive

# Draw detected grid polygons back onto the source image.
vis = image.copy()
h, w = image.shape[:2]
try:
    grids = detect_grids(binary)
    for i, g in enumerate(grids):
        for cell in g.cells:
            pts = np.array([[int(x * w), int(y * h)] for x, y in cell.polygon], np.int32)
            cv2.polylines(vis, [pts], True, (0, 0, 255), 2)
    print(f"detect_grids -> {len(grids)} grid(s): "
          f"{[(getattr(g,'rows',None), getattr(g,'cols',None), len(g.cells)) for g in grids]}")
except Exception as e:
    print(f"detect_grids raised: {type(e).__name__}: {e}")
cv2.imwrite(str(out / "3_detected.png"), vis)

# Which detector fired, in isolation:
for name, fn in [("rectangular", detect_rectangular_grids), ("irregular", detect_irregular_grids)]:
    try:
        gs = fn(binary)
        print(f"{name}: {len(gs)} grid(s)")
    except Exception as e:
        print(f"{name}: {type(e).__name__}: {e}")
```

Then **Read the output PNGs** (`1_binary.png`, `2_linemask.png`,
`3_detected.png`) — the Read tool renders them. Check in order:

1. `1_binary.png` — grid lines must be **white** and unbroken. If faint/broken,
   the problem is `preprocess.binarize` (block size / C), not detection.
2. `2_linemask.png` — should be *just* the lattice, letters/clues gone. Missing
   borders → kernel too long (`extract_line_mask` h/v size); leftover text →
   kernel too short.
3. `3_detected.png` — red polygons should tile the real cells. Compare against
   the printed rows/cols and the per-detector output.

## Tuning knobs by stage

- `preprocess.binarize` — `block_size`, the `C=10` constant.
- `rectangle.extract_line_mask` — `h_size`/`v_size` (and the `_FINE_KERNEL_RATIO`
  second pass in `detect_rectangular_grids`).
- `segmentation.infer_cell_boxes` — `min_value` (0.4×), `min_gap` (4.0).
- `rectangle` filters — `_MIN_ABS_AREA`, `_PITCH_TOLERANCE`.
- `irregular` — `_MIN_CELL_AREA`, `_SIZE_BAND_LO/HI`, `_ADJ_DILATE`, `_MIN_CELLS`.
- `combined._OVERLAP_FRACTION` — rectangular-vs-irregular dedup.

After changing a constant, re-run and re-check the PNGs, and run `pytest
tests/test_fixtures.py` so a tuning fix doesn't regress the real scans.

## Reproduce as a test

Once diagnosed, capture it: a clean case → add a `synthetic.make_grid` assertion;
a real scan → drop the image in `tests/fixtures/` and assert only the rows/cols
you verified from `3_detected.png`.
