import { describe, it, expect, beforeEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";
import { MenuBar } from "../MenuBar.tsx";
import { useEditor } from "../../state/store.ts";
import type { Cell, Cwd } from "../../model/cwd.ts";
import { createLine } from "../../annotations/types.ts";

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

function loadGrid(): void {
  useEditor
    .getState()
    .loadDocument(doc3x3(), { element: {} as HTMLImageElement, width: 100, height: 100 }, "g.cwd");
}

const colourInputs = (container: HTMLElement) =>
  Array.from(container.querySelectorAll<HTMLInputElement>('input[type="color"]'));

describe("MenuBar colour pickers", () => {
  beforeEach(() => {
    loadGrid();
    cleanup();
  });

  it("applies the highlight to the selected cell when a colour is chosen, as one undo step", () => {
    const s = useEditor.getState();
    s.selectCell(0, 0);
    const undoDepth = useEditor.getState().past.length;

    const { container } = render(<MenuBar onError={() => {}} />);
    const [, highlightInput] = colourInputs(container);
    fireEvent.change(highlightInput!, { target: { value: "#00ff00" } });

    expect(useEditor.getState().doc!.grids[0]!.cells[0]!.background).toEqual([0, 255, 0]);
    expect(useEditor.getState().past.length).toBe(undoDepth + 1);
  });

  it("does nothing to the document when nothing is selected", () => {
    const before = useEditor.getState().doc;
    const { container } = render(<MenuBar onError={() => {}} />);
    const [, highlightInput] = colourInputs(container);
    fireEvent.change(highlightInput!, { target: { value: "#00ff00" } });

    expect(useEditor.getState().doc).toBe(before);
    expect(useEditor.getState().highlight).toEqual([0, 255, 0]); // still updates the picker
  });

  it("recolours the selected annotation when the text colour is chosen", () => {
    const s = useEditor.getState();
    const line = createLine([0, 0], [100, 100], null);
    s.addAnnotation(line);
    s.selectAnnotation(line.id);

    const { container } = render(<MenuBar onError={() => {}} />);
    const [textInput] = colourInputs(container);
    fireEvent.change(textInput!, { target: { value: "#0000ff" } });

    expect(useEditor.getState().doc!.annotations[0]!.colour).toEqual([255, 0, 0]);
  });

  it("clears the highlight of the selected cell via the Clear highlight button", () => {
    const s = useEditor.getState();
    s.selectCell(0, 0);
    s.applyHighlightToSelection();
    expect(useEditor.getState().doc!.grids[0]!.cells[0]!.background).not.toBeNull();

    const { getByRole } = render(<MenuBar onError={() => {}} />);
    fireEvent.click(getByRole("button", { name: "Clear highlight" }));

    expect(useEditor.getState().doc!.grids[0]!.cells[0]!.background).toBeNull();
  });
});
