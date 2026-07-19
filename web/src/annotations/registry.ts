/** The annotation-kind registry and the generic operations built on it. Every
 * call site (renderer, hit-tester, pointer input) works through these helpers,
 * so adding a kind means registering it here — nothing else special-cases it. */

import type { Point } from "../model/geometry.ts";
import { imageToCanvas, type Viewport } from "../canvas/viewport.ts";
import type { Cwd } from "../model/cwd.ts";
import type { AnnotationKind, Handle } from "./kind.ts";
import { handleRadius } from "./sizes.ts";
import type { Annotation, AnnotationType } from "./types.ts";
import { textKind } from "./text.ts";
import { lineKind } from "./line.ts";
import { curveKind } from "./curve.ts";

const KINDS: { [K in AnnotationType]: AnnotationKind<Extract<Annotation, { type: K }>> } = {
  text: textKind,
  line: lineKind,
  curve: curveKind,
};

/** The kind implementation for an annotation. The cast is the single place the
 * union is widened; each kind's methods only ever receive their own variant. */
function kindFor(a: Annotation): AnnotationKind {
  return KINDS[a.type] as unknown as AnnotationKind;
}

export function renderAnnotation(ctx: CanvasRenderingContext2D, vp: Viewport, a: Annotation): void {
  kindFor(a).render(ctx, vp, a);
}

export function annotationHandles(a: Annotation): Handle[] {
  return kindFor(a).handles(a);
}

/** Selection bounds of `a` in canvas pixels, as [x, y, width, height]. */
export function annotationBounds(
  ctx: CanvasRenderingContext2D,
  vp: Viewport,
  a: Annotation,
): [number, number, number, number] {
  return kindFor(a).bounds(ctx, vp, a);
}

export function moveAnnotationBy(a: Annotation, dx: number, dy: number): Annotation {
  return kindFor(a).moveBy(a, dx, dy);
}

export function moveAnnotationHandle(a: Annotation, handleId: string, point: Point): Annotation {
  return kindFor(a).moveHandle(a, handleId, point);
}

/** The id of the topmost annotation under canvas point (cx, cy), or null.
 * Later annotations render on top, so they are tested first. */
export function hitTestAnnotations(
  ctx: CanvasRenderingContext2D,
  doc: Cwd,
  vp: Viewport,
  cx: number,
  cy: number,
): string | null {
  for (let i = doc.annotations.length - 1; i >= 0; i--) {
    const a = doc.annotations[i]!;
    if (kindFor(a).hitTest(ctx, vp, a, cx, cy)) return a.id;
  }
  return null;
}

/** The id of the handle of `a` under canvas point (cx, cy), or null. */
export function hitTestHandle(
  vp: Viewport,
  a: Annotation,
  cx: number,
  cy: number,
): string | null {
  const r = handleRadius(vp);
  for (const h of annotationHandles(a)) {
    const [hx, hy] = imageToCanvas(vp, h.point);
    if (Math.hypot(cx - hx, cy - hy) <= r) return h.id;
  }
  return null;
}
