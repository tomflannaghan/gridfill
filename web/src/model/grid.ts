/** Grid navigation, ported verbatim from python/src/gridfill/types.py.
 *
 * The `.cwd` cells list is already in reading order (row-major for rectangular
 * grids; top-to-bottom then left-to-right by centroid for irregular ones). All
 * geometry-agnostic navigation is expressed as indices into that flat list; the
 * only geometry-dependent piece is `neighbor`.
 */

import { cellCentre, type Grid } from "./cwd.ts";
import { convexHull, type Point } from "./geometry.ts";

export type Direction = "up" | "down" | "left" | "right";

const DIRECTION_VECTORS: Record<Direction, [number, number]> = {
  up: [0, -1],
  down: [0, 1],
  left: [-1, 0],
  right: [1, 0],
};

/** Index of the cell adjacent to `cells[index]` in `direction`, or null.
 * Mirrors `RectangularGrid.neighbor` / `IrregularGrid.neighbor`. */
export function neighbor(grid: Grid, index: number, direction: Direction): number | null {
  return grid.type === "rectangular"
    ? rectangularNeighbor(grid.rows, grid.cols, index, direction)
    : irregularNeighbor(grid, index, direction);
}

function rectangularNeighbor(
  rows: number,
  cols: number,
  index: number,
  direction: Direction,
): number | null {
  const row = Math.floor(index / cols);
  const col = index % cols;
  const drow = direction === "up" ? -1 : direction === "down" ? 1 : 0;
  const dcol = direction === "left" ? -1 : direction === "right" ? 1 : 0;
  const nrow = row + drow;
  const ncol = col + dcol;
  if (nrow >= 0 && nrow < rows && ncol >= 0 && ncol < cols) {
    return nrow * cols + ncol;
  }
  return null;
}

/** Nearest cell whose centre lies in `direction` within a 60-degree cone,
 * scored by `distance * (1 + angle / 45)` so off-axis cells (e.g. the
 * offset rows of a brickwork grid) lose to a farther but better-aligned one. */
function irregularNeighbor(
  grid: { cells: Grid["cells"] },
  index: number,
  direction: Direction,
): number | null {
  const [dx, dy] = DIRECTION_VECTORS[direction];
  const origin = grid.cells[index];
  if (!origin) return null;
  const [ox, oy] = cellCentre(origin);
  let best: number | null = null;
  let bestScore = Infinity;
  for (let i = 0; i < grid.cells.length; i++) {
    if (i === index) continue;
    const [px, py] = cellCentre(grid.cells[i]!);
    const vx = px - ox;
    const vy = py - oy;
    const along = vx * dx + vy * dy;
    if (along <= 0) continue; // behind, or perpendicular to, the direction
    const lateral = Math.abs(vx * dy - vy * dx);
    const angle = (Math.atan2(lateral, along) * 180) / Math.PI;
    if (angle > 60) continue; // outside the 60-degree cone
    const distance = Math.hypot(vx, vy);
    const score = distance * (1 + angle / 45);
    if (score < bestScore) {
      best = i;
      bestScore = score;
    }
  }
  return best;
}

/** The grid's outer boundary, in the same pixel space as cell polygons.
 * Mirrors `RectangularGrid.bounding_polygon` / `IrregularGrid.bounding_polygon`. */
export function boundingPolygon(grid: Grid): Point[] {
  if (grid.type === "rectangular") {
    const { rows, cols, cells } = grid;
    const cell = (r: number, c: number): Point[] => cells[r * cols + c]!.polygon;
    return [
      cell(0, 0)[0]!,
      cell(0, cols - 1)[1]!,
      cell(rows - 1, cols - 1)[2]!,
      cell(rows - 1, 0)[3]!,
    ];
  }
  return convexHull(grid.cells.flatMap((c) => c.polygon));
}

/** The next selectable cell in reading order after `index`, skipping `block`
 * cells (used for type-to-fill auto-advance). Null if none remain. */
export function nextFillable(grid: Grid, index: number): number | null {
  for (let i = index + 1; i < grid.cells.length; i++) {
    if (grid.cells[i]!.kind !== "block") return i;
  }
  return null;
}

/** The previous selectable cell in reading order before `index`, skipping
 * `block` cells (used for crossword-style backspace). Null if none remain. */
export function prevFillable(grid: Grid, index: number): number | null {
  for (let i = index - 1; i >= 0; i--) {
    if (grid.cells[i]!.kind !== "block") return i;
  }
  return null;
}
