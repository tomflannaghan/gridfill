/** Shared stroking for line/curve annotations: draw a polyline (in canvas
 * pixels) with round caps and joins. */

import type { Point } from "../model/geometry.ts";

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
