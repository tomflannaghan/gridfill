/** Polygon geometry helpers, ported from python/src/gridfill/geometry.py.
 *
 * These operate on points in any consistent coordinate space (source-image
 * pixels for document geometry, canvas pixels for hit-testing) as long as
 * both the polygon and the test point share it.
 */

export type Point = [number, number];

/** Mean of a polygon's vertices — a cheap, good-enough cell centre.
 * Mirrors `polygon_centroid` in the Python geometry module. */
export function polygonCentroid(polygon: Point[]): Point {
  const n = polygon.length;
  let sx = 0;
  let sy = 0;
  for (const [x, y] of polygon) {
    sx += x;
    sy += y;
  }
  return [sx / n, sy / n];
}

/** True if (x, y) lies inside `polygon` (crossing-number test). Points exactly
 * on an edge may return either result; that is fine for click hit-testing. */
export function pointInPolygon(x: number, y: number, polygon: Point[]): boolean {
  let inside = false;
  const n = polygon.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const pi = polygon[i]!;
    const pj = polygon[j]!;
    const [xi, yi] = pi;
    const [xj, yj] = pj;
    const intersects = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

/** Counter-clockwise convex hull of `points` (Andrew's monotone chain).
 * Ported from `convex_hull` in the Python geometry module. */
export function convexHull(points: Point[]): Point[] {
  const pts = [...new Map(points.map((p) => [`${p[0]},${p[1]}`, p])).values()].sort((a, b) =>
    a[0] === b[0] ? a[1] - b[1] : a[0] - b[0],
  );
  if (pts.length <= 2) return pts;
  const cross = (o: Point, a: Point, b: Point): number =>
    (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower: Point[] = [];
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2]!, lower[lower.length - 1]!, p) <= 0) {
      lower.pop();
    }
    lower.push(p);
  }
  const upper: Point[] = [];
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i]!;
    while (upper.length >= 2 && cross(upper[upper.length - 2]!, upper[upper.length - 1]!, p) <= 0) {
      upper.pop();
    }
    upper.push(p);
  }
  return [...lower.slice(0, -1), ...upper.slice(0, -1)];
}

/** Shortest distance from point (px, py) to the segment a-b. Used to hit-test
 * lines and curves (as a flattened polyline). Degenerate segments (a == b)
 * reduce to the distance to that point. */
export function distanceToSegment(px: number, py: number, a: Point, b: Point): number {
  const [ax, ay] = a;
  const [bx, by] = b;
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  const t = lenSq === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lenSq));
  const cx = ax + t * dx;
  const cy = ay + t * dy;
  return Math.hypot(px - cx, py - cy);
}

/** Shortest distance from (px, py) to a polyline (sequence of connected points).
 * Returns Infinity for a polyline with no segments. */
export function distanceToPolyline(px: number, py: number, points: Point[]): number {
  let best = Infinity;
  for (let i = 0; i < points.length - 1; i++) {
    best = Math.min(best, distanceToSegment(px, py, points[i]!, points[i + 1]!));
  }
  return best;
}

/** Axis-aligned bounds of a set of points, as [minX, minY, maxX, maxY]. */
export function boundsOf(points: Point[]): [number, number, number, number] {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [x, y] of points) {
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  }
  return [minX, minY, maxX, maxY];
}
