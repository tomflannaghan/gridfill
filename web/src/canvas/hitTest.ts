/** Map a canvas-space point to the grid cell under it. Cell tests run in
 * source-image pixel coordinates (cell polygons are stored in image pixels).
 * Annotation hit-testing lives in annotations/registry.ts (it dispatches per
 * kind). */

import type { Cwd } from "../model/cwd.ts";
import { pointInPolygon } from "../model/geometry.ts";
import { canvasToImage, type Viewport } from "./viewport.ts";
import type { Selection } from "../state/store.ts";

/** The cell under canvas point (cx, cy), or null. Searches all grids. */
export function hitTestCell(doc: Cwd, vp: Viewport, cx: number, cy: number): Selection | null {
  const [ix, iy] = canvasToImage(vp, cx, cy);
  for (let gi = 0; gi < doc.grids.length; gi++) {
    const cells = doc.grids[gi]!.cells;
    for (let ci = 0; ci < cells.length; ci++) {
      if (pointInPolygon(ix, iy, cells[ci]!.polygon)) return { gridIndex: gi, cellIndex: ci };
    }
  }
  return null;
}

/** Every cell (across all grids) with at least one polygon vertex inside the
 * image-pixel rectangle `rect` ([x0, y0, x1, y1], corners in any order). Used
 * for marquee selection — a cell is caught if the rectangle touches any of its
 * corners. */
export function cellsInRect(doc: Cwd, rect: [number, number, number, number]): Selection[] {
  const minX = Math.min(rect[0], rect[2]);
  const maxX = Math.max(rect[0], rect[2]);
  const minY = Math.min(rect[1], rect[3]);
  const maxY = Math.max(rect[1], rect[3]);
  const out: Selection[] = [];
  for (let gi = 0; gi < doc.grids.length; gi++) {
    const cells = doc.grids[gi]!.cells;
    for (let ci = 0; ci < cells.length; ci++) {
      const inside = cells[ci]!.polygon.some(
        ([x, y]) => x >= minX && x <= maxX && y >= minY && y <= maxY,
      );
      if (inside) out.push({ gridIndex: gi, cellIndex: ci });
    }
  }
  return out;
}
