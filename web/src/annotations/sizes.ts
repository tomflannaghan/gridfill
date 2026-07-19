/** Screen-space sizes for annotations, all derived from the viewport so they
 * scale with the displayed image (and stay identical between the interactive
 * canvas and the export). */

import type { Viewport } from "../canvas/viewport.ts";
import type { Cwd } from "../model/cwd.ts";

/** Displayed image height in canvas pixels — the basis for every size below. */
function imageHeightPx(vp: Viewport): number {
  return vp.imgH * vp.scale;
}

/** Font size (px) for text annotations that predate the persisted `fontSize`
 * field, scaled to the viewport so old documents still render sensibly. */
export function annotationFontSize(vp: Viewport): number {
  return Math.max(8, imageHeightPx(vp) * 0.02);
}

/** Font-size-to-cell-diameter ratio a cell's letter is drawn at (see
 * `canvas/render.ts`); new text annotations default to the same ratio so they
 * start out visually consistent with grid letters. */
export const LETTER_FONT_RATIO = 0.62;

/** Fallback default (source-image pixels) for a document with no sized cell to
 * seed from. */
export const DEFAULT_TEXT_ANNOTATION_SIZE = 24;

/** Default font size (source-image pixels) for a newly created text
 * annotation: the first grid's first sized, non-block cell's letter size, or
 * `DEFAULT_TEXT_ANNOTATION_SIZE` for a document with no such cell. */
export function defaultTextAnnotationSize(doc: Cwd): number {
  for (const grid of doc.grids) {
    for (const cell of grid.cells) {
      if (cell.kind !== "block" && cell.size != null) return cell.size * LETTER_FONT_RATIO;
    }
  }
  return DEFAULT_TEXT_ANNOTATION_SIZE;
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
