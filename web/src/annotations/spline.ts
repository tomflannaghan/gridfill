/** Smooth-curve helpers: a Catmull-Rom spline through a sequence of anchor
 * points, used to render and hit-test `curve` annotations. Catmull-Rom passes
 * exactly through every anchor, so the anchors double as editing handles.
 *
 * Operates in any consistent coordinate space (normalized or canvas pixels).
 */

import type { Point } from "../model/geometry.ts";

/** Segments per span between consecutive anchors when flattening to a polyline. */
const SAMPLES_PER_SPAN = 16;

/** Catmull-Rom interpolation of one span p1->p2 (p0, p3 are the neighbours). */
function interpolate(p0: Point, p1: Point, p2: Point, p3: Point, t: number): Point {
  const t2 = t * t;
  const t3 = t2 * t;
  const f = (a: number, b: number, c: number, d: number): number =>
    0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
  return [f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])];
}

/** Flatten anchor points into a dense polyline following the Catmull-Rom spline.
 * With fewer than 3 anchors the anchors are returned unchanged (a straight
 * segment or a single point). */
export function splinePolyline(anchors: Point[]): Point[] {
  if (anchors.length < 3) return anchors;
  const out: Point[] = [anchors[0]!];
  for (let i = 0; i < anchors.length - 1; i++) {
    const p0 = anchors[i === 0 ? 0 : i - 1]!;
    const p1 = anchors[i]!;
    const p2 = anchors[i + 1]!;
    const p3 = anchors[i + 2 <= anchors.length - 1 ? i + 2 : anchors.length - 1]!;
    for (let s = 1; s <= SAMPLES_PER_SPAN; s++) {
      out.push(interpolate(p0, p1, p2, p3, s / SAMPLES_PER_SPAN));
    }
  }
  return out;
}
