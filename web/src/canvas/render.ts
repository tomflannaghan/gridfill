/** All canvas drawing for the editor. Pure functions of state + viewport so the
 * same code renders both the interactive canvas and the (chrome-free) export.
 */

import { cellCentre, type Cell, type Cwd, type Grid } from "../model/cwd.ts";
import { bgrToCss } from "../model/color.ts";
import { boundingPolygon } from "../model/grid.ts";
import { boundsOf, polygonCentroid, type Point } from "../model/geometry.ts";
import { normToCanvas, type Viewport } from "./viewport.ts";
import type { Selection } from "../state/store.ts";

const BLOCK_FILL = "#0d0d0d";
// Default colour for letters and annotations when they carry no explicit
// `textColor` (black); an element's own BGR colour overrides it.
const DEFAULT_TEXT_COLOR = "#000000";
const ACTIVE_GRID_BORDER = "#2fbf5f";
const SELECT_STROKE = "#123ec4";
const MULTI_SELECT_STROKE = "#e07a1f";
const CELL_INSET = 0.08;

export interface Scene {
  doc: Cwd;
  viewport: Viewport;
  image: HTMLImageElement;
  selection: Selection | null;
  mode: "normal" | "multiEntry";
  /** Draw selection / active-grid chrome. False for image export. */
  showChrome: boolean;
}

export function renderScene(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { doc, viewport: vp, image } = scene;
  ctx.drawImage(image, vp.offsetX, vp.offsetY, vp.imgW * vp.scale, vp.imgH * vp.scale);

  for (const grid of doc.grids) {
    for (const cell of grid.cells) drawCell(ctx, vp, cell);
  }

  drawAnnotations(ctx, scene);

  if (scene.showChrome) drawChrome(ctx, scene);
}

function pathPolygon(ctx: CanvasRenderingContext2D, vp: Viewport, polygon: Point[]): void {
  ctx.beginPath();
  polygon.forEach((p, i) => {
    const [x, y] = normToCanvas(vp, p);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
}

/** Shrink a polygon toward its centroid so a fill doesn't bleed onto grid lines. */
function insetPolygon(polygon: Point[], frac: number): Point[] {
  const [cx, cy] = polygonCentroid(polygon);
  return polygon.map(([x, y]) => [cx + (x - cx) * (1 - frac), cy + (y - cy) * (1 - frac)]);
}

function drawCell(ctx: CanvasRenderingContext2D, vp: Viewport, cell: Cell): void {
  if (cell.kind === "block") {
    pathPolygon(ctx, vp, cell.polygon);
    ctx.fillStyle = BLOCK_FILL;
    ctx.fill();
    return;
  }
  if (cell.background) {
    pathPolygon(ctx, vp, insetPolygon(cell.polygon, CELL_INSET));
    ctx.fillStyle = bgrToCss(cell.background);
    ctx.fill();
  }
  if (cell.letter) drawLetter(ctx, vp, cell);
}

function drawLetter(ctx: CanvasRenderingContext2D, vp: Viewport, cell: Cell): void {
  const canvasPts = cell.polygon.map((p) => normToCanvas(vp, p));
  const [minX, minY, maxX, maxY] = boundsOf(canvasPts);
  const w = maxX - minX;
  const h = maxY - minY;
  const [cx, cy] = normToCanvas(vp, cellCentre(cell));
  const text = cell.letter ?? "";

  let fontSize = Math.min(w, h) * 0.62;
  ctx.font = `600 ${fontSize}px system-ui, sans-serif`;
  const measured = ctx.measureText(text).width;
  const maxWidth = w * 0.82;
  if (measured > maxWidth && measured > 0) {
    fontSize *= maxWidth / measured;
    ctx.font = `600 ${fontSize}px system-ui, sans-serif`;
  }
  ctx.fillStyle = cell.textColor ? bgrToCss(cell.textColor) : DEFAULT_TEXT_COLOR;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, cx, cy);
}

function drawAnnotations(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { doc, viewport: vp } = scene;
  const fontSize = Math.max(11, vp.imgH * vp.scale * 0.02);
  ctx.font = `500 ${fontSize}px system-ui, sans-serif`;
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  for (const [nx, ny, text, color] of doc.annotations) {
    const [x, y] = normToCanvas(vp, [nx, ny]);
    ctx.fillStyle = color ? bgrToCss(color) : DEFAULT_TEXT_COLOR;
    ctx.fillText(text, x, y);
  }
}

function drawChrome(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { doc, viewport: vp, selection, mode } = scene;
  if (!selection) return;
  const grid = doc.grids[selection.gridIndex] as Grid | undefined;
  if (!grid) return;

  // Green border around the active grid.
  pathPolygon(ctx, vp, boundingPolygon(grid));
  ctx.strokeStyle = ACTIVE_GRID_BORDER;
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.stroke();

  // Selected-cell indicator.
  const cell = grid.cells[selection.cellIndex];
  if (cell) {
    pathPolygon(ctx, vp, cell.polygon);
    ctx.strokeStyle = mode === "multiEntry" ? MULTI_SELECT_STROKE : SELECT_STROKE;
    ctx.lineWidth = mode === "multiEntry" ? 3.5 : 2.5;
    ctx.stroke();
    ctx.fillStyle = mode === "multiEntry" ? "rgba(224,122,31,0.14)" : "rgba(18,62,196,0.12)";
    ctx.fill();
  }
}
