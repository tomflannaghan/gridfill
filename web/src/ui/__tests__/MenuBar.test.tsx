import { describe, it, expect, beforeEach, vi } from "vitest";
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

  it("applies the highlight via the pill's apply button, then clears it on a second click", () => {
    const s = useEditor.getState();
    s.selectCell(0, 0);

    const { getByRole } = render(<MenuBar onError={() => {}} />);
    const applyHighlight = getByRole("button", { name: "Apply or clear highlight" });

    fireEvent.click(applyHighlight);
    expect(useEditor.getState().doc!.grids[0]!.cells[0]!.background).toEqual(s.highlight);

    fireEvent.click(applyHighlight);
    expect(useEditor.getState().doc!.grids[0]!.cells[0]!.background).toBeNull();
  });

  it("applies the text colour via the pill's apply button", () => {
    const s = useEditor.getState();
    s.setTextColour([10, 20, 30]);
    s.selectCell(0, 0);

    const { getByRole } = render(<MenuBar onError={() => {}} />);
    fireEvent.click(getByRole("button", { name: "Apply text colour" }));

    expect(useEditor.getState().doc!.grids[0]!.cells[0]!.textColour).toEqual([10, 20, 30]);
  });
});

describe("MenuBar document lifecycle", () => {
  beforeEach(() => {
    loadGrid();
    cleanup();
    vi.restoreAllMocks();
  });

  it("closes the document when the logo is clicked, with no unsaved changes", () => {
    const { getByRole } = render(<MenuBar onError={() => {}} />);
    fireEvent.click(getByRole("button", { name: "Gridfill" }));

    expect(useEditor.getState().doc).toBeNull();
  });

  it("warns before closing the document via the logo if there are unsaved changes, and respects Cancel", () => {
    useEditor.getState().selectCell(0, 0);
    useEditor.getState().typeChar("A");
    expect(useEditor.getState().dirty).toBe(true);

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { getByRole } = render(<MenuBar onError={() => {}} />);
    fireEvent.click(getByRole("button", { name: "Gridfill" }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(useEditor.getState().doc).not.toBeNull();

    confirmSpy.mockReturnValue(true);
    fireEvent.click(getByRole("button", { name: "Gridfill" }));
    expect(useEditor.getState().doc).toBeNull();
  });

  it("warns before opening a new file if there are unsaved changes", () => {
    useEditor.getState().selectCell(0, 0);
    useEditor.getState().typeChar("A");

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { getByRole, container } = render(<MenuBar onError={() => {}} />);
    const fileInput = container.querySelector<HTMLInputElement>("input.hidden-file-input")!;
    const clickSpy = vi.spyOn(fileInput, "click");

    fireEvent.click(getByRole("button", { name: "Open" }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(clickSpy).not.toHaveBeenCalled();
  });

  it("does not warn when opening a new file with no unsaved changes", () => {
    const confirmSpy = vi.spyOn(window, "confirm");
    const { getByRole, container } = render(<MenuBar onError={() => {}} />);
    const fileInput = container.querySelector<HTMLInputElement>("input.hidden-file-input")!;
    const clickSpy = vi.spyOn(fileInput, "click");

    fireEvent.click(getByRole("button", { name: "Open" }));

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
  });

  it("clears the dirty flag after Save", () => {
    useEditor.getState().selectCell(0, 0);
    useEditor.getState().typeChar("A");
    expect(useEditor.getState().dirty).toBe(true);

    // saveCwd triggers a real download; stub the pieces it touches (jsdom has
    // no createObjectURL/revokeObjectURL implementation to spy on).
    URL.createObjectURL = vi.fn().mockReturnValue("blob:mock");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const { getByRole } = render(<MenuBar onError={() => {}} />);
    fireEvent.click(getByRole("button", { name: "Save" }));

    expect(useEditor.getState().dirty).toBe(false);
  });
});
