/** Mapping between the source image's coordinate spaces and the canvas.
 *
 * The document stores polygon/annotation coordinates as source-image pixel
 * positions. The viewport fits that image into the canvas preserving aspect
 * ratio (letterboxed), giving a uniform scale plus a centring offset -- the
 * image-to-canvas map is therefore isotropic (the same scale factor along
 * both axes and for any length). All values here are in CSS pixels;
 * device-pixel-ratio scaling is applied separately on the canvas context.
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

/** Fit a pixel sub-region of the image into the canvas, centred, so that
 * region (e.g. the selected grid) fills the view. `margin` is the fraction of
 * the canvas kept as padding on each side so the region doesn't touch the
 * edges. `region` is `[minX, minY, maxX, maxY]` in source-image pixels. */
export function computeViewportForRegion(
  canvasW: number,
  canvasH: number,
  imgW: number,
  imgH: number,
  region: [number, number, number, number],
  margin = 0.06,
): Viewport {
  const [minX, minY, maxX, maxY] = region;
  const regionW = Math.max(maxX - minX, 1e-6);
  const regionH = Math.max(maxY - minY, 1e-6);
  const usableW = canvasW * (1 - 2 * margin);
  const usableH = canvasH * (1 - 2 * margin);
  const scale = Math.min(usableW / regionW, usableH / regionH);
  const centreX = (minX + maxX) / 2;
  const centreY = (minY + maxY) / 2;
  const offsetX = canvasW / 2 - centreX * scale;
  const offsetY = canvasH / 2 - centreY * scale;
  return { scale, offsetX, offsetY, imgW, imgH };
}

/** Source-image pixel point -> canvas pixel. */
export function imageToCanvas(vp: Viewport, [ix, iy]: Point): Point {
  return [ix * vp.scale + vp.offsetX, iy * vp.scale + vp.offsetY];
}

/** Canvas pixel -> source-image pixel point (may fall outside the image). */
export function canvasToImage(vp: Viewport, cx: number, cy: number): Point {
  return [(cx - vp.offsetX) / vp.scale, (cy - vp.offsetY) / vp.scale];
}

/** Length in source-image pixels -> canvas pixels. Isotropic (the viewport
 * scale is uniform in x and y), so this works for any length -- a polygon
 * edge, `Cell.size` (the incircle diameter), a stroke width. */
export function imageLengthToCanvas(vp: Viewport, n: number): number {
  return n * vp.scale;
}
