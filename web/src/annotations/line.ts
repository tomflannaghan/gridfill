/** The `line` annotation kind: a straight line between two endpoint handles. */

import { boundsOf, distanceToSegment, type Point } from "../model/geometry.ts";
import { normToCanvas } from "../canvas/viewport.ts";
import type { AnnotationKind, Handle } from "./kind.ts";
import { annotationColour } from "./kind.ts";
import { annotationStrokeWidth, handleRadius } from "./sizes.ts";
import { strokePolyline } from "./stroke.ts";
import type { LineAnnotation } from "./types.ts";

export const lineKind: AnnotationKind<LineAnnotation> = {
  render(ctx, vp, a) {
    const pts = a.points.map((p) => normToCanvas(vp, p));
    strokePolyline(ctx, pts, annotationColour(a.colour), annotationStrokeWidth(vp));
  },

  hitTest(_ctx, vp, a, cx, cy) {
    const [p0, p1] = a.points.map((p) => normToCanvas(vp, p)) as [Point, Point];
    const tol = Math.max(handleRadius(vp), annotationStrokeWidth(vp));
    return distanceToSegment(cx, cy, p0, p1) <= tol;
  },

  bounds(_ctx, vp, a) {
    const [minX, minY, maxX, maxY] = boundsOf(a.points.map((p) => normToCanvas(vp, p)));
    return [minX, minY, maxX - minX, maxY - minY];
  },

  handles(a): Handle[] {
    return a.points.map((point, i) => ({ id: String(i), point }));
  },

  moveBy(a, dx, dy) {
    const points: [Point, Point] = [
      [a.points[0][0] + dx, a.points[0][1] + dy],
      [a.points[1][0] + dx, a.points[1][1] + dy],
    ];
    return { ...a, points };
  },

  moveHandle(a, handleId, point) {
    const i = Number(handleId);
    if (i !== 0 && i !== 1) return a;
    const points: [Point, Point] = [a.points[0], a.points[1]];
    points[i] = point;
    return { ...a, points };
  },
};
