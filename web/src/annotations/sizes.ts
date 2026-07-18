/** Screen-space sizes for annotations, all derived from the viewport so they
 * scale with the displayed image (and stay identical between the interactive
 * canvas and the export). */

import type { Viewport } from "../canvas/viewport.ts";

/** Displayed image height in canvas pixels — the basis for every size below. */
function imageHeightPx(vp: Viewport): number {
  return vp.imgH * vp.scale;
}

/** Font size (px) for text annotations. */
export function annotationFontSize(vp: Viewport): number {
  return Math.max(8, imageHeightPx(vp) * 0.02);
}

/** Stroke width (px) for line and curve annotations. */
export function annotationStrokeWidth(vp: Viewport): number {
  return Math.max(1, imageHeightPx(vp) * 0.0025);
}

/** Radius (px) of the draggable editing handles shown on a selected annotation.
 * Also the pointer tolerance for grabbing a handle or a thin line. */
export function handleRadius(vp: Viewport): number {
  return Math.max(5, imageHeightPx(vp) * 0.009);
}
