/** Shared stroking for line/curve annotations: draw a polyline (in canvas
 * pixels) with round caps and joins, at the annotation's own width. */

import type { Point } from "../model/geometry.ts";
import { imageLengthToCanvas, type Viewport } from "../canvas/viewport.ts";
import { annotationStrokeWidth } from "./sizes.ts";
import type { StrokedAnnotation } from "./types.ts";

/** The canvas-pixel stroke width for `a`: its own persisted width, converted
 * from source-image pixels, or the legacy viewport-relative default for
 * annotations that predate the `lineWidth` field. */
export function canvasStrokeWidth(vp: Viewport, a: StrokedAnnotation): number {
  return a.lineWidth != null
    ? Math.max(1, imageLengthToCanvas(vp, a.lineWidth))
    : annotationStrokeWidth(vp);
}

export function strokePolyline(
  ctx: CanvasRenderingContext2D,
  points: Point[],
  colour: string,
  width: number,
): void {
  if (points.length < 2) return;
  ctx.beginPath();
  ctx.moveTo(points[0]![0], points[0]![1]);
  for (let i = 1; i < points.length; i++) ctx.lineTo(points[i]![0], points[i]![1]);
  ctx.strokeStyle = colour;
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke();
}
