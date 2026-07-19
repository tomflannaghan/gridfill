import { describe, it, expect } from "vitest";
import type { Cell, Cwd } from "../../model/cwd.ts";
import { cellsInRect } from "../hitTest.ts";

// A cell is an 80px square centred on (cx, cy): vertices at (cx±40, cy±40).
function square(cx: number, cy: number): Cell {
  const s = 40;
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
    size: null,
  };
}

// 3x3 lattice (row-major), cells on a 100px pitch.
function doc3x3(): Cwd {
  const cells: Cell[] = [];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) cells.push(square(col * 100, row * 100));
  }
  return {
    format: "gridfill",
    version: 2,
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
    expect(idx(cellsInRect(doc3x3(), [-50, -50, 50, 50]))).toEqual([0]);
  });

  it("catches every cell the rectangle touches across a row", () => {
    // Wide enough to reach the third column's vertices (x up to 240).
    expect(idx(cellsInRect(doc3x3(), [-50, -50, 250, 50]))).toEqual([0, 1, 2]);
  });

  it("normalizes corners given in any order", () => {
    // Same box as the first case but with corners reversed.
    expect(idx(cellsInRect(doc3x3(), [50, 50, -50, -50]))).toEqual([0]);
  });

  it("returns nothing when the rectangle misses every vertex", () => {
    // A tiny box in the gap between cells (cells span ±40 around each pitch).
    expect(cellsInRect(doc3x3(), [45, 45, 55, 55])).toEqual([]);
  });

  it("selects a cell fully containing the rectangle, with no vertex of either shape inside the other", () => {
    // A small box entirely inside the top-left cell (which spans ±40): none of
    // the cell's vertices fall in the box, and none of the box's corners are
    // outside the cell, so a vertex-only test would miss this overlap.
    expect(idx(cellsInRect(doc3x3(), [-10, -10, 10, 10]))).toEqual([0]);
  });

  it("selects a cell the rectangle only touches through crossing edges", () => {
    // A wide, short strip through the middle of the top-left cell: it pokes
    // out past the cell's left/right edges (but stays short of the next
    // column's cell, which starts at x=60), so neither the cell's vertices
    // fall inside the strip nor the strip's corners fall inside the cell —
    // only the edges cross.
    expect(idx(cellsInRect(doc3x3(), [-55, -10, 55, 10]))).toEqual([0]);
  });
});
