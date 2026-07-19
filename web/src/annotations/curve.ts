/** The `curve` annotation kind: a smooth Catmull-Rom spline through its anchor
 * points. Each anchor is a draggable handle. */

import { boundsOf, distanceToPolyline, type Point } from "../model/geometry.ts";
import { imageToCanvas } from "../canvas/viewport.ts";
import type { AnnotationKind, Handle } from "./kind.ts";
import { annotationColour } from "./kind.ts";
import { annotationStrokeWidth, handleRadius } from "./sizes.ts";
import { strokePolyline } from "./stroke.ts";
import { splinePolyline } from "./spline.ts";
import type { CurveAnnotation } from "./types.ts";

/** The curve flattened to a canvas-space polyline (the smoothed path). */
function curvePolyline(vp: Parameters<typeof imageToCanvas>[0], a: CurveAnnotation): Point[] {
  return splinePolyline(a.points.map((p) => imageToCanvas(vp, p)));
}

export const curveKind: AnnotationKind<CurveAnnotation> = {
  render(ctx, vp, a) {
    strokePolyline(ctx, curvePolyline(vp, a), annotationColour(a.colour), annotationStrokeWidth(vp));
  },

  hitTest(_ctx, vp, a, cx, cy) {
    const tol = Math.max(handleRadius(vp), annotationStrokeWidth(vp));
    return distanceToPolyline(cx, cy, curvePolyline(vp, a)) <= tol;
  },

  bounds(_ctx, vp, a) {
    const [minX, minY, maxX, maxY] = boundsOf(curvePolyline(vp, a));
    return [minX, minY, maxX - minX, maxY - minY];
  },

  handles(a): Handle[] {
    return a.points.map((point, i) => ({ id: String(i), point }));
  },

  moveBy(a, dx, dy) {
    return { ...a, points: a.points.map(([x, y]): Point => [x + dx, y + dy]) };
  },

  moveHandle(a, handleId, point) {
    const i = Number(handleId);
    if (!Number.isInteger(i) || i < 0 || i >= a.points.length) return a;
    const points = a.points.slice();
    points[i] = point;
    return { ...a, points };
  },
};
