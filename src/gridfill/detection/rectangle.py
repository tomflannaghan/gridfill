"""Grid detection and perspective rectification.

Detection is driven purely off the line lattice, which is present in both blocked
and barred grids -- we never rely on black blocks existing.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..errors import GridDetectionError, GridSegmentationError, MultipleGridsError
from ..segmentation import infer_cell_boxes
from ..types import BoundingBox, Cell, Point, RectangularGrid


@dataclass
class _RectifiedLattice:
    """The rectified grid lattice plus the transform that produced it.

    Purely an internal intermediate: nothing outside this module needs the
    rectified mask or transform once the public functions below have turned it
    into a :class:`RectangularGrid`.
    """

    # Rectified, axis-aligned binary line mask containing just the grid lattice.
    line_mask: np.ndarray
    # 3x3 perspective transform from source -> rectified coords.
    transform: np.ndarray
    # (width, height) of the rectified space, for warping other source layers.
    size: tuple[int, int]


def extract_line_mask(
    binary: np.ndarray, h_size: int | None = None, v_size: int | None = None
) -> np.ndarray:
    """Isolate the long horizontal and vertical strokes (grid lines).

    Morphological opening with long 1-D kernels keeps only runs longer than the
    kernel, which removes letters and clue numbers while preserving grid lines.
    *h_size*/*v_size* default to a fraction of the image's own width/height, which
    is right for a page's main grid(s) but too large for a single-row/column
    auxiliary grid, whose border strokes span only one cell -- see
    :func:`detect_grids`, which re-extracts with smaller, pitch-derived sizes to
    recover those.
    """
    height, width = binary.shape[:2]
    if h_size is None:
        h_size = max(10, width // 20)
    if v_size is None:
        v_size = max(10, height // 20)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_size, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    return np.asarray(cv2.bitwise_or(horizontal, vertical))


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Order four points as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    coord_sum = pts.sum(axis=1)
    coord_diff = np.diff(pts, axis=1).ravel()
    rect[0] = pts[np.argmin(coord_sum)]  # top-left: smallest x + y
    rect[2] = pts[np.argmax(coord_sum)]  # bottom-right: largest x + y
    rect[1] = pts[np.argmin(coord_diff)]  # top-right: smallest y - x
    rect[3] = pts[np.argmax(coord_diff)]  # bottom-left: largest y - x
    return rect


_MIN_ABS_AREA = 16.0
_ROW_BAND_FRAC = 0.10


def _contour_to_quad(contour: np.ndarray) -> np.ndarray:
    """Approximate a contour as an ordered 4-corner quad."""
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
    if len(approx) == 4:
        quad = approx.reshape(4, 2).astype(np.float32)
    else:
        quad = cv2.boxPoints(cv2.minAreaRect(contour)).astype(np.float32)
    return _order_corners(quad)


def _find_grid_quads(line_mask: np.ndarray) -> list[np.ndarray]:
    """Find quads for all grid lattices, sorted in reading order.

    Candidates are filtered on absolute area only (not relative to the
    largest grid found): a single-row or single-column grid can be far
    smaller in area than a neighbouring full grid, so a size-ratio cutoff
    would discard it. Non-lattice shapes that sneak past this floor (stray
    strokes, badges) get rejected later when they fail to segment into a
    row/column lattice.
    """
    contours, _ = cv2.findContours(line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise GridDetectionError("No line structure found in image")

    h = line_mask.shape[0]

    quads: list[tuple[float, float, np.ndarray]] = []
    for contour in contours:
        if cv2.contourArea(contour) < _MIN_ABS_AREA:
            continue
        quad = _contour_to_quad(contour)
        cx = float(quad[:, 0].mean())
        cy = float(quad[:, 1].mean())
        quads.append((cy, cx, quad))

    row_band = h * _ROW_BAND_FRAC
    quads.sort(key=lambda t: (t[0], t[1]))
    rows: list[list[tuple[float, float, np.ndarray]]] = []
    for item in quads:
        if rows and abs(item[0] - rows[-1][0][0]) < row_band:
            rows[-1].append(item)
        else:
            rows.append([item])
    for row in rows:
        row.sort(key=lambda t: t[1])

    return [quad for row in rows for _, _, quad in row]


def _rectify_quad(line_mask: np.ndarray, quad: np.ndarray) -> _RectifiedLattice:
    """Compute a perspective-rectified lattice from a single quad."""
    top_left, top_right, bottom_right, bottom_left = quad

    width = int(
        round(
            max(
                np.linalg.norm(top_right - top_left),
                np.linalg.norm(bottom_right - bottom_left),
            )
        )
    )
    height = int(
        round(
            max(
                np.linalg.norm(bottom_left - top_left),
                np.linalg.norm(bottom_right - top_right),
            )
        )
    )
    if width < 2 or height < 2:
        raise GridDetectionError(f"Degenerate grid size: {width}x{height}")

    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(quad, dst)
    rectified = cv2.warpPerspective(line_mask, transform, (width, height))
    return _RectifiedLattice(line_mask=rectified, transform=transform, size=(width, height))


def _polygon_from_box(
    box: BoundingBox, inverse: np.ndarray, src_size: tuple[int, int]
) -> list[Point]:
    """Project a rectified-space box's 4 corners back to normalized source coords."""
    src_w, src_h = src_size
    corners = np.array(
        [[box.x, box.y], [box.x2, box.y], [box.x2, box.y2], [box.x, box.y2]],
        dtype=np.float64,
    )
    homogeneous = np.hstack([corners, np.ones((4, 1))])
    projected = homogeneous @ inverse.T
    projected = projected[:, :2] / projected[:, 2:3]
    projected[:, 0] /= src_w
    projected[:, 1] /= src_h
    return [(float(x), float(y)) for x, y in projected]


def _build_rectangular_grid(
    src_shape: tuple[int, ...], lattice: _RectifiedLattice, boxes: list[list[BoundingBox]]
) -> RectangularGrid:
    """Turn a rectified lattice's cell boxes into a grid, projected onto the source image."""
    rows, cols = len(boxes), len(boxes[0])
    inverse = np.linalg.inv(lattice.transform)
    src_h, src_w = src_shape[:2]
    cells = [
        Cell(polygon=_polygon_from_box(box, inverse, (src_w, src_h)))
        for row in boxes
        for box in row
    ]
    return RectangularGrid(rows=rows, cols=cols, cells=cells)


def _segment_quad(
    line_mask: np.ndarray, quad: np.ndarray
) -> tuple[_RectifiedLattice, list[list[BoundingBox]]] | None:
    """Rectify and segment one candidate quad, or None if it isn't a real lattice."""
    try:
        lattice = _rectify_quad(line_mask, quad)
        boxes = infer_cell_boxes(lattice.line_mask)
    except (GridDetectionError, GridSegmentationError):
        return None
    return lattice, boxes


def _cell_pitch(lattice: _RectifiedLattice, boxes: list[list[BoundingBox]]) -> tuple[float, float]:
    """Average (col_pitch, row_pitch) -- i.e. per-cell width and height -- of a lattice."""
    rows, cols = len(boxes), len(boxes[0])
    width, height = lattice.size
    return width / cols, height / rows


_PITCH_TOLERANCE = 0.20
_FINE_KERNEL_RATIO = 0.6


def _resolve_candidates(
    line_mask: np.ndarray,
) -> list[tuple[_RectifiedLattice, list[list[BoundingBox]]]]:
    return [
        result for quad in _find_grid_quads(line_mask) if (result := _segment_quad(line_mask, quad))
    ]


def detect_rectangular_grids(binary: np.ndarray) -> list[RectangularGrid]:
    """Detect all rectangular crossword grids in the image, sorted in reading order.

    Candidate quads that don't resolve into a row/column lattice at all (too
    few lines, a degenerate size) are skipped outright. Quads that do, but
    whose cell size is way off from the page's dominant grid -- a badge, logo,
    or stray stroke that happens to bound a tiny 1x1 or 2x1 lattice -- are
    skipped too: real auxiliary grids on a crossword page (including
    single-row/single-column ones) share the same cell pitch as the main
    grid, so a mismatch is a strong signal it isn't actually a grid.
    """
    coarse_mask = extract_line_mask(binary)
    candidates = _resolve_candidates(coarse_mask)
    if not candidates:
        raise GridDetectionError("No valid grid lattice found in image")

    reference_lattice, reference_boxes = max(candidates, key=lambda c: len(c[1]) * len(c[1][0]))
    ref_col_pitch, ref_row_pitch = _cell_pitch(reference_lattice, reference_boxes)

    # The coarse mask's kernel is sized off the whole image, so it erases the
    # border strokes of a single-row/column grid (only one cell pitch long) even
    # though it correctly preserves the main grid's much longer borders. Re-extract
    # with a kernel sized off the now-known reference pitch to recover those, and
    # fold the result into the coarse mask so nothing found there is lost.
    fine_h = max(10, int(ref_col_pitch * _FINE_KERNEL_RATIO))
    fine_v = max(10, int(ref_row_pitch * _FINE_KERNEL_RATIO))
    fine_mask = extract_line_mask(binary, h_size=fine_h, v_size=fine_v)
    merged_mask = np.asarray(cv2.bitwise_or(coarse_mask, fine_mask))
    candidates = _resolve_candidates(merged_mask)

    grids: list[RectangularGrid] = []
    for lattice, boxes in candidates:
        col_pitch, row_pitch = _cell_pitch(lattice, boxes)
        if (
            abs(col_pitch - ref_col_pitch) > _PITCH_TOLERANCE * ref_col_pitch
            or abs(row_pitch - ref_row_pitch) > _PITCH_TOLERANCE * ref_row_pitch
        ):
            continue
        grids.append(_build_rectangular_grid(binary.shape, lattice, boxes))
    if not grids:
        raise GridDetectionError("No valid grid lattice found in image")
    return grids


def detect_grid(binary: np.ndarray, grid_index: int | None = None) -> RectangularGrid:
    """Locate a crossword lattice on the page and segment it into a grid.

    When the image contains multiple grids, *grid_index* (1-based, reading
    left-to-right then top-to-bottom) selects which grid to return. If the
    image contains a single grid, *grid_index* may be omitted.

    Raises :class:`MultipleGridsError` when multiple grids are found and no
    *grid_index* is given, or :class:`GridSegmentationError` if a lattice is
    found but its cells can't be resolved into rows/columns.
    """
    grids = detect_rectangular_grids(binary)

    if grid_index is None:
        if len(grids) == 1:
            return grids[0]
        raise MultipleGridsError(len(grids))

    if grid_index < 1 or grid_index > len(grids):
        raise GridDetectionError(
            f"grid_index {grid_index} out of range; image has {len(grids)} grid(s)"
        )
    return grids[grid_index - 1]
