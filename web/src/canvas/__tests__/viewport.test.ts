import { describe, it, expect } from "vitest";
import {
  computeViewport,
  computeViewportForRegion,
  imageLengthToCanvas,
  imageToCanvas,
} from "../viewport.ts";

describe("computeViewportForRegion", () => {
  it("centres the region in the canvas", () => {
    // A region occupying the middle 20% of a 1000x800 image (pixel box
    // [400,320,600,480], centred on image pixel (500,400)), fit into a
    // 1000x1000 canvas: its centre should map to the canvas centre.
    const vp = computeViewportForRegion(1000, 1000, 1000, 800, [400, 320, 600, 480]);
    const [cx, cy] = imageToCanvas(vp, [500, 400]);
    expect(cx).toBeCloseTo(500, 6);
    expect(cy).toBeCloseTo(500, 6);
  });

  it("scales the region to fill the canvas up to the margin", () => {
    // A square region in a square image fit into a square canvas: with a 6%
    // margin each side the region spans 88% of the canvas.
    const vp = computeViewportForRegion(1000, 1000, 1000, 1000, [250, 250, 750, 750], 0.06);
    const [x0] = imageToCanvas(vp, [250, 250]);
    const [x1] = imageToCanvas(vp, [750, 750]);
    expect(x1 - x0).toBeCloseTo(880, 4);
    expect(x0).toBeCloseTo(60, 4);
  });

  it("zooms in more than the whole-image fit", () => {
    const region = computeViewportForRegion(1000, 1000, 1000, 1000, [300, 300, 700, 700]);
    const whole = computeViewport(1000, 1000, 1000, 1000);
    expect(region.scale).toBeGreaterThan(whole.scale);
  });

  it("preserves aspect ratio (uniform scale) for a non-square region", () => {
    const vp = computeViewportForRegion(1000, 600, 1000, 1000, [100, 200, 900, 400]);
    // scale is a single number; an equal pixel delta in x and y maps to an
    // equal canvas delta in x and y.
    const [ax, ay] = imageToCanvas(vp, [100, 200]);
    const [bx, by] = imageToCanvas(vp, [200, 300]);
    expect(bx - ax).toBeCloseTo(by - ay, 6);
  });
});

describe("imageLengthToCanvas", () => {
  it("scales a pixel length isotropically, independent of image orientation", () => {
    // A 60px cell diameter in a 340x440 (portrait) image, canvas fit at
    // scale 2 (canvas 680x880): the length just scales with the viewport.
    const portrait = computeViewport(680, 880, 340, 440);
    expect(imageLengthToCanvas(portrait, 60)).toBeCloseTo(120, 6);

    // Same real length, landscape image: still just scale x length.
    const landscape = computeViewport(880, 680, 440, 340);
    expect(imageLengthToCanvas(landscape, 60)).toBeCloseTo(120, 6);
  });
});
