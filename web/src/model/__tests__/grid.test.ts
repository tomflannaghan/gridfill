import { describe, it, expect } from "vitest";
import type { Cell, Grid, IrregularGrid, RectangularGrid } from "../cwd.ts";
import { neighbor, nextFillable, prevFillable, type Direction } from "../grid.ts";

function square(cx: number, cy: number, s = 0.4): Cell {
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
    centre: null,
    size: null,
  };
}

// A 3x3 lattice of unit squares in reading order (row-major).
function grid3x3Cells(): Cell[] {
  const cells: Cell[] = [];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) cells.push(square(col, row));
  }
  return cells;
}

// Ground truth from the Python IrregularGrid.neighbor / RectangularGrid.neighbor
// (see the port note in grid.ts). Both grid types agree on this lattice.
const EXPECTED: Record<number, Record<Direction, number | null>> = {
  0: { up: null, down: 3, left: null, right: 1 },
  1: { up: null, down: 4, left: 0, right: 2 },
  2: { up: null, down: 5, left: 1, right: null },
  3: { up: 0, down: 6, left: null, right: 4 },
  4: { up: 1, down: 7, left: 3, right: 5 },
  5: { up: 2, down: 8, left: 4, right: null },
  6: { up: 3, down: null, left: null, right: 7 },
  7: { up: 4, down: null, left: 6, right: 8 },
  8: { up: 5, down: null, left: 7, right: null },
};

const DIRS: Direction[] = ["up", "down", "left", "right"];

describe("neighbor", () => {
  it("matches Python for a rectangular 3x3 grid", () => {
    const grid: RectangularGrid = { type: "rectangular", rows: 3, cols: 3, cells: grid3x3Cells() };
    for (let i = 0; i < 9; i++) {
      for (const d of DIRS) expect(neighbor(grid, i, d)).toBe(EXPECTED[i]![d]);
    }
  });

  it("matches Python for an irregular 3x3 grid (cone search)", () => {
    const grid: IrregularGrid = { type: "irregular", cells: grid3x3Cells() };
    for (let i = 0; i < 9; i++) {
      for (const d of DIRS) expect(neighbor(grid, i, d)).toBe(EXPECTED[i]![d]);
    }
  });
});

describe("neighbor (60-degree cone with angle-penalised scoring)", () => {
  it("prefers a farther but well-aligned cell over a closer off-axis one", () => {
    // From the origin, going "right": cell 1 is directly ahead but farther
    // (distance 1.5, angle 0 -> score 1.5); cell 2 is nearer but 45 degrees
    // off-axis (distance ~1.414, angle 45 -> score ~2.828). The old
    // along+lateral scoring picked the nearer-but-diagonal cell (this is the
    // brickwork case: offset cells in the row above/below are closer than
    // the true row neighbour but aren't the natural left/right choice).
    const cells: Cell[] = [
      square(0, 0), // 0: origin
      square(1.5, 0), // 1: aligned, farther
      square(1 / Math.SQRT2, 1 / Math.SQRT2), // 2: 45 degrees off, nearer
    ];
    const grid: IrregularGrid = { type: "irregular", cells };
    expect(neighbor(grid, 0, "right")).toBe(1);
  });

  it("widens the cone to 60 degrees (a 45-degree cone would miss this cell)", () => {
    const angle = (50 * Math.PI) / 180;
    const cells: Cell[] = [
      square(0, 0), // 0: origin
      square(Math.cos(angle), Math.sin(angle)), // 1: 50 degrees off-axis
    ];
    const grid: IrregularGrid = { type: "irregular", cells };
    expect(neighbor(grid, 0, "right")).toBe(1);
  });
});

describe("reading-order fill navigation", () => {
  it("skips block cells when advancing and stepping back", () => {
    const cells = grid3x3Cells();
    cells[1]!.kind = "block";
    cells[2]!.kind = "block";
    const grid: Grid = { type: "rectangular", rows: 3, cols: 3, cells };
    expect(nextFillable(grid, 0)).toBe(3); // skip the two blocks at 1,2
    expect(nextFillable(grid, 3)).toBe(4);
    expect(nextFillable(grid, 8)).toBe(null);
    expect(prevFillable(grid, 3)).toBe(0); // skip blocks at 1,2 going back
    expect(prevFillable(grid, 0)).toBe(null);
  });
});
