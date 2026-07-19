/** The `text` annotation kind: free text anchored at its top-left. It has no
 * geometry handles — it is moved by dragging its body and its text is edited via
 * the inline editor (double-click). */

import { imageLengthToCanvas, imageToCanvas, type Viewport } from "../canvas/viewport.ts";
import type { AnnotationKind } from "./kind.ts";
import { annotationColour } from "./kind.ts";
import { annotationFontSize } from "./sizes.ts";
import type { TextAnnotation } from "./types.ts";

/** The canvas `font` string for a text annotation at the given size. */
export function textFont(fontSize: number): string {
  return `500 ${fontSize}px system-ui, sans-serif`;
}

/** The canvas-pixel font size for `a`: its own persisted size, converted from
 * source-image pixels, or the legacy viewport-relative default for
 * annotations that predate the `fontSize` field. */
export function canvasFontSize(vp: Viewport, a: TextAnnotation): number {
  return a.fontSize != null ? imageLengthToCanvas(vp, a.fontSize) : annotationFontSize(vp);
}

export const textKind: AnnotationKind<TextAnnotation> = {
  render(ctx, vp, a) {
    ctx.font = textFont(canvasFontSize(vp, a));
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillStyle = annotationColour(a.colour);
    const [x, y] = imageToCanvas(vp, [a.x, a.y]);
    ctx.fillText(a.text, x, y);
  },

  hitTest(ctx, vp, a, cx, cy) {
    const [x, y, w, h] = this.bounds(ctx, vp, a);
    return cx >= x && cx <= x + w && cy >= y && cy <= y + h;
  },

  bounds(ctx, vp, a) {
    const fontSize = canvasFontSize(vp, a);
    ctx.font = textFont(fontSize);
    const [x, y] = imageToCanvas(vp, [a.x, a.y]);
    return [x, y, ctx.measureText(a.text).width, fontSize];
  },

  handles() {
    return [];
  },

  moveBy(a, dx, dy) {
    return { ...a, x: a.x + dx, y: a.y + dy };
  },

  moveHandle(a) {
    return a;
  },
};
