/** Map a canvas-space point to the grid cell under it. Cell tests run in
 * normalized coordinates (cell polygons are stored normalized). Annotation
 * hit-testing lives in annotations/registry.ts (it dispatches per kind). */

import type { Cwd } from "../model/cwd.ts";
import { pointInPolygon } from "../model/geometry.ts";
import { canvasToNorm, type Viewport } from "./viewport.ts";
import type { Selection } from "../state/store.ts";

/** The cell under canvas point (cx, cy), or null. Searches all grids. */
export function hitTestCell(doc: Cwd, vp: Viewport, cx: number, cy: number): Selection | null {
  const [nx, ny] = canvasToNorm(vp, cx, cy);
  for (let gi = 0; gi < doc.grids.length; gi++) {
    const cells = doc.grids[gi]!.cells;
    for (let ci = 0; ci < cells.length; ci++) {
      if (pointInPolygon(nx, ny, cells[ci]!.polygon)) return { gridIndex: gi, cellIndex: ci };
    }
  }
  return null;
}
