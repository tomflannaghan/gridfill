import { describe, it, expect } from "vitest";
import {
  computeViewport,
  computeViewportForRegion,
  normToCanvas,
} from "../viewport.ts";

describe("computeViewportForRegion", () => {
  it("centres the region in the canvas", () => {
    // A region occupying the middle 20% of a 1000x800 image, fit into a
    // 1000x1000 canvas: its centre should map to the canvas centre.
    const vp = computeViewportForRegion(1000, 1000, 1000, 800, [0.4, 0.4, 0.6, 0.6]);
    const [cx, cy] = normToCanvas(vp, [0.5, 0.5]);
    expect(cx).toBeCloseTo(500, 6);
    expect(cy).toBeCloseTo(500, 6);
  });

  it("scales the region to fill the canvas up to the margin", () => {
    // A square region in a square image fit into a square canvas: with a 6%
    // margin each side the region spans 88% of the canvas.
    const vp = computeViewportForRegion(1000, 1000, 1000, 1000, [0.25, 0.25, 0.75, 0.75], 0.06);
    const [x0] = normToCanvas(vp, [0.25, 0.25]);
    const [x1] = normToCanvas(vp, [0.75, 0.75]);
    expect(x1 - x0).toBeCloseTo(880, 4);
    expect(x0).toBeCloseTo(60, 4);
  });

  it("zooms in more than the whole-image fit", () => {
    const region = computeViewportForRegion(1000, 1000, 1000, 1000, [0.3, 0.3, 0.7, 0.7]);
    const whole = computeViewport(1000, 1000, 1000, 1000);
    expect(region.scale).toBeGreaterThan(whole.scale);
  });

  it("preserves aspect ratio (uniform scale) for a non-square region", () => {
    const vp = computeViewportForRegion(1000, 600, 1000, 1000, [0.1, 0.2, 0.9, 0.4]);
    // scale is a single number; a normalized unit square maps to a canvas square.
    const [ax, ay] = normToCanvas(vp, [0.1, 0.2]);
    const [bx, by] = normToCanvas(vp, [0.2, 0.3]);
    expect(bx - ax).toBeCloseTo(by - ay, 6);
  });
});
