"""Irregular grid detection.

Unlike rectangular detection (``rectangle.py``), which isolates an axis-aligned
line lattice and projects it onto the X/Y axes, this module makes no assumption
about cell shape. It treats a grid as a *collection of similarly-sized cells
that tile a continuous, adjacent lattice*, and finds cells directly as the
enclosed white regions bounded by the ink lines. That works for rhombi,
hexagons, curved wedges and plain squares alike.

The pipeline: close small gaps in the ink, label the enclosed background
regions, drop the page background and noise, keep the dominant same-size
cluster, group mutually-adjacent cells into separate lattices, and trace each
cell's polygon.

First-cut limitations (by design, to be refined later):

* A solidly filled (blocked) cell has no white interior, so it is not detected.
* Heavily curved cell edges collapse to a coarse polygon approximation.
* Rectangular grids satisfy this definition too and are detected as irregular
  grids -- telling the two apart is future work.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..errors import GridDetectionError
from ..types import Cell, IrregularGrid, Point

# Close ink gaps so every cell interior is fully enclosed before labelling.
_GAP_CLOSE_KERNEL = 3
_GAP_CLOSE_ITERS = 1

# Absolute pixel floor for a candidate region: drops speckle and the counters of
# printed glyphs (the holes in "O"/"A"/...), which are far smaller than a cell.
_MIN_CELL_AREA = 60
# A single cell can't plausibly span more than this fraction of the whole image.
_MAX_CELL_AREA_FRAC = 0.2
# Keep regions whose area is within this band of the reference (dominant) cell
# area -- this is the "similarly sized" test.
_SIZE_BAND_LO = 0.4
_SIZE_BAND_HI = 2.5

# Bridge distance (px) used to decide two cells are adjacent across a thin wall.
_ADJ_DILATE = 6
# A lattice needs at least this many cells to count as a grid.
_MIN_CELLS = 4

# approxPolyDP epsilon as a fraction of the contour perimeter.
_APPROX_EPS_RATIO = 0.02
# Reading-order row band, as a fraction of the median cell height.
_CELL_ROW_BAND = 0.5
# Reading-order row band for whole grids, as a fraction of image height.
_GRID_ROW_BAND = 0.15


def _label_regions(binary: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Label the enclosed background regions of the (ink=255) binary image.

    Returns ``(labels, stats, centroids)`` from
    :func:`cv2.connectedComponentsWithStats`. Label 0 is the ink itself; every
    other label is a white region (a cell interior, or the page background).
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (_GAP_CLOSE_KERNEL, _GAP_CLOSE_KERNEL))
    closed = cv2.dilate(binary, kernel, iterations=_GAP_CLOSE_ITERS)
    interior = np.asarray((closed == 0).astype(np.uint8) * 255)
    _, labels, stats, centroids = cv2.connectedComponentsWithStats(interior, connectivity=4)
    return labels, stats, centroids


def _touches_border(stats_row: np.ndarray, shape: tuple[int, int]) -> bool:
    height, width = shape
    x = int(stats_row[cv2.CC_STAT_LEFT])
    y = int(stats_row[cv2.CC_STAT_TOP])
    w = int(stats_row[cv2.CC_STAT_WIDTH])
    h = int(stats_row[cv2.CC_STAT_HEIGHT])
    return x == 0 or y == 0 or x + w == width or y + h == height


def _select_cells(labels: np.ndarray, stats: np.ndarray) -> list[int]:
    """Pick the region labels that look like cells: not the border-touching
    background, above the noise floor, and within the dominant size cluster."""
    height, width = labels.shape
    max_area = _MAX_CELL_AREA_FRAC * height * width

    candidates: list[int] = []
    areas: list[float] = []
    for label in range(1, stats.shape[0]):
        area = float(stats[label, cv2.CC_STAT_AREA])
        if area < _MIN_CELL_AREA or area > max_area:
            continue
        if _touches_border(stats[label], (height, width)):
            continue
        candidates.append(label)
        areas.append(area)

    if not candidates:
        return []

    # Reference cell area is the median of the *upper half* of candidate areas,
    # so a crowd of small leftovers (glyph counters that cleared the floor)
    # can't drag the reference below the true cell size.
    areas_arr = np.array(areas)
    upper = areas_arr[areas_arr >= np.median(areas_arr)]
    reference = float(np.median(upper))

    lo, hi = _SIZE_BAND_LO * reference, _SIZE_BAND_HI * reference
    return [label for label, area in zip(candidates, areas, strict=True) if lo <= area <= hi]


def _build_adjacency(
    labels: np.ndarray, stats: np.ndarray, cells: list[int]
) -> dict[int, set[int]]:
    """Adjacency graph over *cells*: two cells are neighbours when their regions
    are separated only by a thin wall (found by dilating one across the wall)."""
    height, width = labels.shape
    cell_set = set(cells)
    adjacency: dict[int, set[int]] = {label: set() for label in cells}
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * _ADJ_DILATE + 1, 2 * _ADJ_DILATE + 1)
    )
    for label in cells:
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        x0, y0 = max(0, x - _ADJ_DILATE), max(0, y - _ADJ_DILATE)
        x1, y1 = min(width, x + w + _ADJ_DILATE), min(height, y + h + _ADJ_DILATE)
        sub = labels[y0:y1, x0:x1]
        grown = cv2.dilate((sub == label).astype(np.uint8), kernel)
        for other in np.unique(sub[(grown > 0) & (sub != label)]):
            other_label = int(other)
            if other_label in cell_set:
                adjacency[label].add(other_label)
                adjacency[other_label].add(label)
    return adjacency


def _connected_groups(cells: list[int], adjacency: dict[int, set[int]]) -> list[list[int]]:
    """Split *cells* into connected components of the adjacency graph."""
    seen: set[int] = set()
    groups: list[list[int]] = []
    for start in cells:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        group: list[int] = []
        while stack:
            node = stack.pop()
            group.append(node)
            for neighbour in adjacency[node]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        groups.append(group)
    return groups


def _cell_polygon(labels: np.ndarray, stats: np.ndarray, label: int) -> list[Point]:
    """Trace one cell region's boundary as a normalized polygon.

    The region is grown back by the gap-closing amount so its boundary sits on
    the wall centre (adjacent cells then meet edge-to-edge), then reduced to a
    handful of vertices. Coordinates are fractions of the source (width, height).
    """
    height, width = labels.shape
    pad = _GAP_CLOSE_KERNEL * _GAP_CLOSE_ITERS + 2
    x = int(stats[label, cv2.CC_STAT_LEFT])
    y = int(stats[label, cv2.CC_STAT_TOP])
    w = int(stats[label, cv2.CC_STAT_WIDTH])
    h = int(stats[label, cv2.CC_STAT_HEIGHT])
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(width, x + w + pad), min(height, y + h + pad)

    mask = (labels[y0:y1, x0:x1] == label).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (_GAP_CLOSE_KERNEL, _GAP_CLOSE_KERNEL))
    mask = cv2.dilate(mask, kernel, iterations=_GAP_CLOSE_ITERS)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour = max(contours, key=cv2.contourArea)
    eps = _APPROX_EPS_RATIO * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, eps, True).reshape(-1, 2)
    return [(float(px + x0) / width, float(py + y0) / height) for px, py in approx]


def _reading_order(items: list[tuple[float, float, int]], band: float) -> list[int]:
    """Sort ``(cy, cx, payload)`` items top-to-bottom in rows, left-to-right
    within a row (rows being centroids grouped within *band* vertically)."""
    ordered = sorted(items, key=lambda t: (t[0], t[1]))
    rows: list[list[tuple[float, float, int]]] = []
    for item in ordered:
        if rows and abs(item[0] - rows[-1][0][0]) < band:
            rows[-1].append(item)
        else:
            rows.append([item])
    for row in rows:
        row.sort(key=lambda t: t[1])
    return [payload for row in rows for _, _, payload in row]


def detect_irregular_grids(binary: np.ndarray) -> list[IrregularGrid]:
    """Detect all irregular grids in a binarized image, in reading order.

    *binary* is an ``ink = 255`` image as produced by
    :func:`gridfill.preprocess.binarize`. Raises :class:`GridDetectionError`
    when no lattice of adjacent same-size cells is found.
    """
    labels, stats, centroids = _label_regions(binary)
    cells = _select_cells(labels, stats)
    if not cells:
        raise GridDetectionError("No cell-like regions found in image")

    adjacency = _build_adjacency(labels, stats, cells)
    groups = [g for g in _connected_groups(cells, adjacency) if len(g) >= _MIN_CELLS]
    if not groups:
        raise GridDetectionError("No irregular grid (adjacent same-size cells) found in image")

    height, width = labels.shape
    grids: list[tuple[float, float, IrregularGrid]] = []
    for group in groups:
        median_h = float(np.median([stats[label, cv2.CC_STAT_HEIGHT] for label in group]))
        cell_items = [
            (float(centroids[label][1]), float(centroids[label][0]), label) for label in group
        ]
        ordered_labels = _reading_order(cell_items, band=_CELL_ROW_BAND * median_h)
        grid_cells = [Cell(polygon=_cell_polygon(labels, stats, label)) for label in ordered_labels]
        group_cx = float(np.mean([centroids[label][0] for label in group]))
        group_cy = float(np.mean([centroids[label][1] for label in group]))
        grids.append((group_cy, group_cx, IrregularGrid(cells=grid_cells)))

    order = _reading_order(
        [(cy, cx, i) for i, (cy, cx, _) in enumerate(grids)], band=_GRID_ROW_BAND * height
    )
    return [grids[i][2] for i in order]
