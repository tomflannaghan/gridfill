/** Polygon geometry helpers, ported from python/src/gridfill/geometry.py.
 *
 * These operate on points in any consistent coordinate space (normalized
 * [0,1] fractions or pixels) as long as both the polygon and the test point
 * share it.
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
