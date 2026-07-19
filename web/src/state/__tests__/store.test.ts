import { describe, it, expect, beforeEach } from "vitest";
import { useEditor } from "../store.ts";
import type { Cell, Cwd } from "../../model/cwd.ts";
import { createLine, createText } from "../../annotations/types.ts";

function emptyDoc(): Cwd {
  return { format: "gridfill", version: 2, image: { encoding: "png", data: "" }, grids: [], annotations: [] };
}

function loadEmpty(): void {
  useEditor
    .getState()
    .loadDocument(emptyDoc(), { element: {} as HTMLImageElement, width: 100, height: 100 }, "t.cwd");
}

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

const cellIndices = () =>
  useEditor
    .getState()
    .selectedCells.map((s) => s.cellIndex)
    .sort((a, b) => a - b);

const cellOf = (i: number): Cell => useEditor.getState().doc!.grids[0]!.cells[i]!;

describe("annotation CRUD", () => {
  beforeEach(loadEmpty);

  it("adds, updates and deletes by id", () => {
    const s = useEditor.getState();
    const text = createText(10, 20, "hi", null);
    s.addAnnotation(text);
    expect(useEditor.getState().doc!.annotations).toHaveLength(1);

    s.updateAnnotation(text.id, { ...text, text: "bye" });
    expect((useEditor.getState().doc!.annotations[0] as typeof text).text).toBe("bye");

    s.deleteAnnotation(text.id);
    expect(useEditor.getState().doc!.annotations).toHaveLength(0);
  });

  it("clears the annotation selection when its annotation is deleted", () => {
    const s = useEditor.getState();
    const line = createLine([0, 0], [100, 100], null);
    s.addAnnotation(line);
    s.selectAnnotation(line.id);
    expect(useEditor.getState().selectedAnnotationId).toBe(line.id);
    s.deleteAnnotation(line.id);
    expect(useEditor.getState().selectedAnnotationId).toBeNull();
  });

  it("deselects cells when an annotation is selected for editing", () => {
    loadGrid();
    const s = useEditor.getState();
    const line = createLine([0, 0], [100, 100], null);
    s.addAnnotation(line);
    s.selectCell(0, 0);
    s.extendSelection("right"); // multi-cell selection
    s.selectAnnotation(line.id);
    expect(useEditor.getState().selection).toBeNull();
    expect(useEditor.getState().selectedCells).toEqual([]);
    expect(useEditor.getState().selectedAnnotationId).toBe(line.id);
  });
});

describe("undo / redo", () => {
  beforeEach(loadEmpty);

  it("undoes and redoes an annotation add", () => {
    const s = useEditor.getState();
    s.addAnnotation(createText(10, 20, "hi", null));
    expect(useEditor.getState().doc!.annotations).toHaveLength(1);

    s.undo();
    expect(useEditor.getState().doc!.annotations).toHaveLength(0);

    s.redo();
    expect(useEditor.getState().doc!.annotations).toHaveLength(1);
  });

  it("does nothing when there is no history", () => {
    const s = useEditor.getState();
    s.undo();
    expect(useEditor.getState().doc!.annotations).toHaveLength(0);
  });

  it("drops the redo stack after a fresh change", () => {
    const s = useEditor.getState();
    s.addAnnotation(createText(0, 0, "a", null));
    s.undo();
    s.addAnnotation(createText(1, 1, "b", null));
    s.redo(); // nothing to redo — the branch was discarded
    const texts = useEditor.getState().doc!.annotations;
    expect(texts).toHaveLength(1);
    expect((texts[0] as { text: string }).text).toBe("b");
  });

  it("preserves the cell selection across undo and redo", () => {
    loadGrid();
    const s = useEditor.getState();
    s.selectCell(0, 4);
    s.typeChar("x"); // commits a change (selection auto-advances)
    s.selectCell(0, 4);
    const sel = useEditor.getState().selection;

    s.undo();
    expect(useEditor.getState().selection).toEqual(sel);
    s.redo();
    expect(useEditor.getState().selection).toEqual(sel);
  });
});

describe("tools", () => {
  beforeEach(loadEmpty);

  it("switching tool clears the annotation selection", () => {
    const s = useEditor.getState();
    const line = createLine([0, 0], [100, 100], null);
    s.addAnnotation(line);
    s.selectAnnotation(line.id);
    s.setTool("line");
    expect(useEditor.getState().tool).toBe("line");
    expect(useEditor.getState().selectedAnnotationId).toBeNull();
  });
});

describe("multi-cell selection", () => {
  beforeEach(loadGrid);

  it("extendSelection accumulates exactly the visited cells", () => {
    const s = useEditor.getState();
    s.selectCell(0, 0);
    s.extendSelection("right"); // -> cell 1
    s.extendSelection("right"); // -> cell 2
    s.extendSelection("down"); // -> cell 5
    expect(useEditor.getState().selection).toEqual({ gridIndex: 0, cellIndex: 5 });
    expect(cellIndices()).toEqual([0, 1, 2, 5]);
  });

  it("extendSelection does not duplicate a revisited cell", () => {
    const s = useEditor.getState();
    s.selectCell(0, 0);
    s.extendSelection("right"); // -> 1
    s.extendSelection("left"); // back to 0 (already in the set)
    expect(cellIndices()).toEqual([0, 1]);
  });

  it("deleteCell clears every selected cell", () => {
    const s = useEditor.getState();
    s.selectCell(0, 0);
    s.typeChar("a"); // cell 0 = A, selection now on cell 1
    s.selectCell(0, 1);
    s.typeChar("b"); // cell 1 = B
    s.selectCell(0, 0);
    s.extendSelection("right"); // cells 0, 1 selected
    s.deleteCell();
    expect(cellOf(0).letter).toBeNull();
    expect(cellOf(1).letter).toBeNull();
    expect(cellOf(0).kind).toBe("empty");
  });

  it("a plain move collapses back to a single selection", () => {
    const s = useEditor.getState();
    s.selectCell(0, 0);
    s.extendSelection("right");
    expect(cellIndices()).toEqual([0, 1]);
    s.move("down");
    expect(useEditor.getState().selectedCells).toEqual([]);
  });

  it("selectCellsInRect selects cells with a vertex in the rectangle", () => {
    const s = useEditor.getState();
    s.selectCellsInRect([-50, -50, 250, 50]); // top row
    expect(cellIndices()).toEqual([0, 1, 2]);
    expect(useEditor.getState().selection).toEqual({ gridIndex: 0, cellIndex: 0 });
  });
});

describe("apply colour to selection", () => {
  beforeEach(loadGrid);

  it("applies the highlight to every selected cell in one undo step", () => {
    const s = useEditor.getState();
    const highlight = s.highlight;
    s.selectCell(0, 0);
    s.extendSelection("right"); // cells 0, 1
    const undoDepth = useEditor.getState().past.length;

    s.applyHighlightToSelection();
    expect(cellOf(0).background).toEqual(highlight);
    expect(cellOf(1).background).toEqual(highlight);
    expect(cellOf(2).background).toBeNull();
    expect(useEditor.getState().past.length).toBe(undoDepth + 1); // single step

    useEditor.getState().undo();
    expect(cellOf(0).background).toBeNull();
    expect(cellOf(1).background).toBeNull();
  });

  it("applies to a single selected cell", () => {
    const s = useEditor.getState();
    s.setTextColour([10, 20, 30]);
    s.selectCell(0, 4);
    s.applyTextColourToSelection();
    expect(cellOf(4).textColour).toEqual([10, 20, 30]);
    expect(cellOf(0).textColour).toBeNull();
  });

  it("applies to the selected annotation instead of cells when one is selected", () => {
    const s = useEditor.getState();
    const line = createLine([0, 0], [100, 100], null);
    s.addAnnotation(line);
    s.selectCell(0, 4); // deselected again by selectAnnotation below
    s.selectAnnotation(line.id);
    s.setTextColour([10, 20, 30]);
    const undoDepth = useEditor.getState().past.length;

    s.applyTextColourToSelection();
    const updated = useEditor.getState().doc!.annotations[0]!;
    expect(updated.colour).toEqual([10, 20, 30]);
    expect(cellOf(4).textColour).toBeNull(); // cell untouched
    expect(useEditor.getState().past.length).toBe(undoDepth + 1); // single step

    useEditor.getState().undo();
    expect(useEditor.getState().doc!.annotations[0]!.colour).toBeNull();
  });

  it("skips block cells and does nothing without a selection", () => {
    const s = useEditor.getState();
    // Make cell 1 a block, then marquee the whole top row.
    useEditor.setState((st) => {
      const cells = st.doc!.grids[0]!.cells.map((c, i) => (i === 1 ? { ...c, kind: "block" as const } : c));
      const grids = [{ ...st.doc!.grids[0]!, cells }];
      return { doc: { ...st.doc!, grids } };
    });
    s.selectCellsInRect([-50, -50, 250, 50]);
    s.applyHighlightToSelection();
    expect(cellOf(1).background).toBeNull(); // block untouched
    expect(cellOf(0).background).not.toBeNull();

    s.clearSelection();
    const before = useEditor.getState().doc;
    s.applyHighlightToSelection(); // no selection -> no-op
    expect(useEditor.getState().doc).toBe(before);
  });
});
