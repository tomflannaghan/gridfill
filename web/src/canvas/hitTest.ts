/** Map a canvas-space point to what's under it: a grid cell, an annotation, or
 * empty space. Cell tests run in normalized coordinates (cell polygons are
 * stored normalized); annotation tests need pixel metrics, so a canvas context
 * is passed in to measure text. */

import type { Cwd } from "../model/cwd.ts";
import { pointInPolygon } from "../model/geometry.ts";
import { canvasToNorm, normToCanvas, type Viewport } from "./viewport.ts";
import type { Selection } from "../state/store.ts";

export function annotationFontSize(vp: Viewport): number {
  return Math.max(11, vp.imgH * vp.scale * 0.02);
}

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

/** The index of the annotation under canvas point (cx, cy), or null. */
export function hitTestAnnotation(
  ctx: CanvasRenderingContext2D,
  doc: Cwd,
  vp: Viewport,
  cx: number,
  cy: number,
): number | null {
  const fontSize = annotationFontSize(vp);
  ctx.font = `500 ${fontSize}px system-ui, sans-serif`;
  // Search topmost (last-drawn) first.
  for (let i = doc.annotations.length - 1; i >= 0; i--) {
    const [anx, any, text] = doc.annotations[i]!;
    const [x, y] = normToCanvas(vp, [anx, any]);
    const w = ctx.measureText(text).width;
    if (cx >= x && cx <= x + w && cy >= y && cy <= y + fontSize) return i;
  }
  return null;
}
