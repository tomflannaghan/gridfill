/** Mapping between the source image's coordinate spaces and the canvas.
 *
 * The document stores polygon/annotation coordinates as [0,1] fractions of the
 * source image size. The viewport fits that image into the canvas preserving
 * aspect ratio (letterboxed), giving a uniform scale plus a centring offset.
 * All values here are in CSS pixels; device-pixel-ratio scaling is applied
 * separately on the canvas context.
 */

import type { Point } from "../model/geometry.ts";

export interface Viewport {
  /** Pixels-per-image-pixel (uniform in x and y). */
  scale: number;
  /** Canvas-space offset of the image's top-left corner. */
  offsetX: number;
  offsetY: number;
  imgW: number;
  imgH: number;
}

/** Fit an `imgW x imgH` image into a `canvasW x canvasH` area, centred. */
export function computeViewport(
  canvasW: number,
  canvasH: number,
  imgW: number,
  imgH: number,
): Viewport {
  const scale = Math.min(canvasW / imgW, canvasH / imgH);
  const offsetX = (canvasW - imgW * scale) / 2;
  const offsetY = (canvasH - imgH * scale) / 2;
  return { scale, offsetX, offsetY, imgW, imgH };
}

/** Normalized [0,1] point -> canvas pixel. */
export function normToCanvas(vp: Viewport, [nx, ny]: Point): Point {
  return [nx * vp.imgW * vp.scale + vp.offsetX, ny * vp.imgH * vp.scale + vp.offsetY];
}

/** Canvas pixel -> normalized [0,1] point (may fall outside [0,1]). */
export function canvasToNorm(vp: Viewport, cx: number, cy: number): Point {
  return [(cx - vp.offsetX) / (vp.imgW * vp.scale), (cy - vp.offsetY) / (vp.imgH * vp.scale)];
}

/** Length in image-normalized units -> canvas pixels along X. */
export function normWidthToCanvas(vp: Viewport, n: number): number {
  return n * vp.imgW * vp.scale;
}
