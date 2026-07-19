import { describe, it, expect } from "vitest";
import { lineKind } from "../line.ts";
import { curveKind } from "../curve.ts";
import type { LineAnnotation, CurveAnnotation } from "../types.ts";
import type { Viewport } from "../../canvas/viewport.ts";

// A 100x100 image mapped 1:1 to canvas pixels.
const VP: Viewport = { scale: 1, offsetX: 0, offsetY: 0, imgW: 100, imgH: 100 };
// line/curve hit-testing ignores the context; a stub is enough.
const CTX = {} as CanvasRenderingContext2D;

const line: LineAnnotation = {
  id: "l",
  type: "line",
  colour: null,
  points: [
    [0, 0],
    [100, 0],
  ],
};

const curve: CurveAnnotation = {
  id: "c",
  type: "curve",
  colour: null,
  points: [
    [0, 0],
    [50, 50],
    [100, 0],
  ],
};

describe("lineKind", () => {
  it("hit-tests near the segment but not far from it", () => {
    expect(lineKind.hitTest(CTX, VP, line, 50, 2)).toBe(true);
    expect(lineKind.hitTest(CTX, VP, line, 50, 40)).toBe(false);
  });

  it("moves both endpoints together", () => {
    const moved = lineKind.moveBy(line, 10, 20);
    expect(moved.points).toEqual([
      [10, 20],
      [110, 20],
    ]);
  });

  it("moves a single endpoint by handle id", () => {
    const moved = lineKind.moveHandle(line, "1", [50, 50]);
    expect(moved.points).toEqual([
      [0, 0],
      [50, 50],
    ]);
  });

  it("exposes an endpoint handle per point", () => {
    expect(lineKind.handles(line).map((h) => h.id)).toEqual(["0", "1"]);
  });
});

describe("curveKind", () => {
  it("hit-tests near the smoothed path", () => {
    expect(curveKind.hitTest(CTX, VP, curve, 50, 50)).toBe(true);
    expect(curveKind.hitTest(CTX, VP, curve, 50, 95)).toBe(false);
  });

  it("moves an anchor by handle id and leaves others put", () => {
    const moved = curveKind.moveHandle(curve, "1", [60, 10]);
    expect(moved.points[1]).toEqual([60, 10]);
    expect(moved.points[0]).toEqual([0, 0]);
  });
});
