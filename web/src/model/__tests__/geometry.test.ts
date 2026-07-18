import { describe, it, expect } from "vitest";
import { pointInPolygon, polygonCentroid, boundsOf, type Point } from "../geometry.ts";

const SQUARE: Point[] = [
  [0, 0],
  [1, 0],
  [1, 1],
  [0, 1],
];

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
