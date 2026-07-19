/** All canvas drawing for the editor. Pure functions of state + viewport so the
 * same code renders both the interactive canvas and the (chrome-free) export.
 */

import { cellCentre, type Cell, type Cwd, type Grid } from "../model/cwd.ts";
import { bgrToCss } from "../model/colour.ts";
import { boundingPolygon } from "../model/grid.ts";
import { boundsOf, polygonCentroid, type Point } from "../model/geometry.ts";
import { normToCanvas, type Viewport } from "./viewport.ts";
import type { Selection, Tool } from "../state/store.ts";
import type { Annotation } from "../annotations/types.ts";
import {
  annotationBounds,
  annotationHandles,
  renderAnnotation,
} from "../annotations/registry.ts";
import { handleRadius } from "../annotations/sizes.ts";

const BLOCK_FILL = "#0d0d0d";
// Default colour for letters and annotations when they carry no explicit
// `textColour` (black); an element's own BGR colour overrides it.
const DEFAULT_TEXT_COLOUR = "#000000";
const ACTIVE_GRID_BORDER = "#2fbf5f";
const SELECT_STROKE = "#123ec4";
const MULTI_SELECT_STROKE = "#e07a1f";
const CELL_INSET = 0.08;

export interface Scene {
  doc: Cwd;
  viewport: Viewport;
  image: HTMLImageElement;
  selection: Selection | null;
  /** Cells in a multi-cell selection, drawn highlighted (chrome only). */
  selectedCells?: Selection[];
  /** Live marquee rectangle [startNorm, currentNorm] while dragging (chrome only). */
  marquee?: [Point, Point] | null;
  mode: "normal" | "multiEntry";
  /** Draw selection / active-grid chrome. False for image export. */
  showChrome: boolean;
  /** The active tool (handles are only shown for the select tool). */
  tool?: Tool;
  /** The selected annotation, whose editing handles are drawn. */
  selectedAnnotationId?: string | null;
  /** An in-progress annotation (a line/curve being drawn, or one being dragged)
   * drawn on top as a live preview. */
  draft?: Annotation | null;
  /** Id of an annotation being dragged: skipped so `draft` replaces it. */
  hiddenAnnotationId?: string | null;
}

export function renderScene(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { doc, viewport: vp, image } = scene;
  ctx.drawImage(image, vp.offsetX, vp.offsetY, vp.imgW * vp.scale, vp.imgH * vp.scale);

  for (const grid of doc.grids) {
    for (const cell of grid.cells) drawCell(ctx, vp, cell);
  }

  drawAnnotations(ctx, scene);

  if (scene.showChrome) {
    drawChrome(ctx, scene);
    drawMarquee(ctx, scene);
    drawAnnotationSelection(ctx, scene);
  }
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
  ctx.fillStyle = cell.textColour ? bgrToCss(cell.textColour) : DEFAULT_TEXT_COLOUR;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, cx, cy);
}

function drawAnnotations(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { doc, viewport: vp, draft, hiddenAnnotationId } = scene;
  for (const a of doc.annotations) {
    if (a.id === hiddenAnnotationId) continue;
    renderAnnotation(ctx, vp, a);
  }
  if (draft) renderAnnotation(ctx, vp, draft);
}

/** Draw the dashed bounding box and handles for the selected annotation (select
 * tool only). While dragging, `draft` carries the live geometry. */
function drawAnnotationSelection(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { doc, viewport: vp, tool, selectedAnnotationId, draft } = scene;
  if (tool !== "select" || !selectedAnnotationId) return;
  const a =
    draft && draft.id === selectedAnnotationId
      ? draft
      : doc.annotations.find((x) => x.id === selectedAnnotationId);
  if (!a) return;

  const [bx, by, bw, bh] = annotationBounds(ctx, vp, a);
  const pad = 3;
  ctx.strokeStyle = SELECT_STROKE;
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 3]);
  ctx.strokeRect(bx - pad, by - pad, bw + 2 * pad, bh + 2 * pad);
  ctx.setLineDash([]);

  const r = handleRadius(vp) * 0.7;
  for (const h of annotationHandles(a)) {
    const [x, y] = normToCanvas(vp, h.point);
    ctx.beginPath();
    ctx.rect(x - r, y - r, 2 * r, 2 * r);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = SELECT_STROKE;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
}

function drawChrome(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { doc, viewport: vp, selection, selectedCells, mode } = scene;
  if (!selection) return;
  const grid = doc.grids[selection.gridIndex] as Grid | undefined;
  if (!grid) return;

  // Green border around the active grid.
  pathPolygon(ctx, vp, boundingPolygon(grid));
  ctx.strokeStyle = ACTIVE_GRID_BORDER;
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.stroke();

  // Multi-cell selection: fill each selected cell (the active cell is drawn
  // more strongly on top below).
  if (selectedCells && selectedCells.length > 1) {
    ctx.fillStyle = "rgba(18,62,196,0.16)";
    ctx.strokeStyle = SELECT_STROKE;
    ctx.lineWidth = 1.5;
    for (const sc of selectedCells) {
      const c = doc.grids[sc.gridIndex]?.cells[sc.cellIndex];
      if (!c) continue;
      pathPolygon(ctx, vp, c.polygon);
      ctx.fill();
      ctx.stroke();
    }
  }

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

/** Draw the live marquee (rubber-band) selection rectangle. */
function drawMarquee(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { viewport: vp, marquee } = scene;
  if (!marquee) return;
  const [ax, ay] = normToCanvas(vp, marquee[0]);
  const [bx, by] = normToCanvas(vp, marquee[1]);
  const x = Math.min(ax, bx);
  const y = Math.min(ay, by);
  const w = Math.abs(bx - ax);
  const h = Math.abs(by - ay);
  ctx.fillStyle = "rgba(18,62,196,0.08)";
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = SELECT_STROKE;
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 3]);
  ctx.strokeRect(x, y, w, h);
  ctx.setLineDash([]);
}
