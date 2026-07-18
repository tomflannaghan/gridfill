import { describe, it, expect } from "vitest";
import { splinePolyline } from "../spline.ts";
import type { Point } from "../../model/geometry.ts";

describe("splinePolyline", () => {
  it("returns the anchors unchanged with fewer than three points", () => {
    const two: Point[] = [
      [0, 0],
      [1, 1],
    ];
    expect(splinePolyline(two)).toEqual(two);
    expect(splinePolyline([[0.5, 0.5]])).toEqual([[0.5, 0.5]]);
  });

  it("passes through every anchor and densifies the path", () => {
    const anchors: Point[] = [
      [0, 0],
      [1, 0],
      [2, 1],
    ];
    const poly = splinePolyline(anchors);
    // First and last samples are the endpoints.
    expect(poly[0]).toEqual([0, 0]);
    expect(poly[poly.length - 1]).toEqual([2, 1]);
    // The middle anchor appears exactly (Catmull-Rom interpolates through it).
    expect(poly.some(([x, y]) => Math.abs(x - 1) < 1e-9 && Math.abs(y - 0) < 1e-9)).toBe(true);
    expect(poly.length).toBeGreaterThan(anchors.length);
  });
});
