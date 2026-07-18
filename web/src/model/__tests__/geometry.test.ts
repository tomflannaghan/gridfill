import { describe, it, expect } from "vitest";
import {
  pointInPolygon,
  polygonCentroid,
  boundsOf,
  distanceToSegment,
  distanceToPolyline,
  type Point,
} from "../geometry.ts";

const SQUARE: Point[] = [
  [0, 0],
  [1, 0],
  [1, 1],
  [0, 1],
];

describe("distanceToSegment", () => {
  it("measures perpendicular distance and clamps to the endpoints", () => {
    const a: Point = [0, 0];
    const b: Point = [10, 0];
    expect(distanceToSegment(5, 3, a, b)).toBeCloseTo(3);
    expect(distanceToSegment(-4, 0, a, b)).toBeCloseTo(4); // past the start
    expect(distanceToSegment(0, 0, a, a)).toBeCloseTo(0); // degenerate segment
  });
});

describe("distanceToPolyline", () => {
  it("returns the nearest segment's distance", () => {
    const poly: Point[] = [
      [0, 0],
      [10, 0],
      [10, 10],
    ];
    expect(distanceToPolyline(10, 5, poly)).toBeCloseTo(0);
    expect(distanceToPolyline(5, 2, poly)).toBeCloseTo(2);
    expect(distanceToPolyline(0, 0, [])).toBe(Infinity);
  });
});

describe("pointInPolygon", () => {
  it("detects interior and exterior points", () => {
    expect(pointInPolygon(0.5, 0.5, SQUARE)).toBe(true);
    expect(pointInPolygon(1.5, 0.5, SQUARE)).toBe(false);
    expect(pointInPolygon(-0.1, 0.5, SQUARE)).toBe(false);
  });

  it("works for a non-convex (L-shaped) polygon", () => {
    const ell: Point[] = [
      [0, 0],
      [2, 0],
      [2, 1],
      [1, 1],
      [1, 2],
      [0, 2],
    ];
    expect(pointInPolygon(0.5, 0.5, ell)).toBe(true); // in the corner
    expect(pointInPolygon(0.5, 1.5, ell)).toBe(true); // in the vertical arm
    expect(pointInPolygon(1.5, 1.5, ell)).toBe(false); // in the missing quadrant
  });
});

describe("polygonCentroid", () => {
  it("returns the mean of vertices", () => {
    expect(polygonCentroid(SQUARE)).toEqual([0.5, 0.5]);
  });
});

describe("boundsOf", () => {
  it("returns min/max bounds", () => {
    expect(boundsOf(SQUARE)).toEqual([0, 0, 1, 1]);
  });
});
