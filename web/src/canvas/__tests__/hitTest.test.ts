import { describe, it, expect } from "vitest";
import type { Cell, Cwd } from "../../model/cwd.ts";
import { cellsInRect } from "../hitTest.ts";

// A cell is a 0.8-wide square centred on (cx, cy): vertices at (cx±0.4, cy±0.4).
function square(cx: number, cy: number): Cell {
  const s = 0.4;
  return {
    polygon: [
      [cx - s, cy - s],
      [cx + s, cy - s],
      [cx + s, cy + s],
      [cx - s, cy + s],
    ],
    kind: "empty",
    letter: null,
    background: null,
    textColour: null,
    centre: [cx, cy],
  };
}

// 3x3 lattice (row-major), cells centred on integer coordinates.
function doc3x3(): Cwd {
  const cells: Cell[] = [];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) cells.push(square(col, row));
  }
  return {
    format: "gridfill",
    version: 1,
    image: { encoding: "png", data: "" },
    grids: [{ type: "rectangular", rows: 3, cols: 3, cells }],
    annotations: [],
  };
}

const idx = (sels: { gridIndex: number; cellIndex: number }[]) =>
  sels.map((s) => s.cellIndex).sort((a, b) => a - b);

describe("cellsInRect", () => {
  it("selects only cells with a vertex inside the rectangle", () => {
    // Covers the top-left cell's vertices only.
    expect(idx(cellsInRect(doc3x3(), [-0.5, -0.5, 0.5, 0.5]))).toEqual([0]);
  });

  it("catches every cell the rectangle touches across a row", () => {
    // Wide enough to reach the third column's vertices (x up to 2.4).
    expect(idx(cellsInRect(doc3x3(), [-0.5, -0.5, 2.5, 0.5]))).toEqual([0, 1, 2]);
  });

  it("normalizes corners given in any order", () => {
    // Same box as the first case but with corners reversed.
    expect(idx(cellsInRect(doc3x3(), [0.5, 0.5, -0.5, -0.5]))).toEqual([0]);
  });

  it("returns nothing when the rectangle misses every vertex", () => {
    // A tiny box in the gap between cells (cells span ±0.4 around integers).
    expect(cellsInRect(doc3x3(), [0.45, 0.45, 0.55, 0.55])).toEqual([]);
  });
});
