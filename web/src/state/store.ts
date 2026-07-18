/** Editor state: the loaded document plus selection / mode / highlight colour,
 * and the mutations behind every editor.md interaction. Kept framework-light
 * (a zustand store) so the canvas can subscribe and redraw imperatively.
 */

import { create } from "zustand";
import type { Annotation, Cell, Cwd, Grid } from "../model/cwd.ts";
import { neighbor, nextFillable, prevFillable, type Direction } from "../model/grid.ts";
import { DEFAULT_HIGHLIGHT_BGR, type Bgr } from "../model/color.ts";

export interface Selection {
  gridIndex: number;
  cellIndex: number;
}

export type Mode = "normal" | "multiEntry";

interface LoadedImage {
  element: HTMLImageElement;
  width: number;
  height: number;
}

export interface EditorState {
  doc: Cwd | null;
  image: LoadedImage | null;
  fileName: string | null;
  selection: Selection | null;
  mode: Mode;
  highlight: Bgr;
  dirty: boolean;

  loadDocument(doc: Cwd, image: LoadedImage, fileName: string | null): void;
  closeDocument(): void;

  selectCell(gridIndex: number, cellIndex: number): void;
  clearSelection(): void;
  enterMultiEntry(gridIndex: number, cellIndex: number): void;
  exitMultiEntry(): void;

  typeChar(ch: string): void;
  backspace(): void;
  deleteCell(): void;
  move(direction: Direction): void;

  toggleHighlight(): void;
  setHighlight(bgr: Bgr): void;

  addAnnotation(x: number, y: number, text: string): number;
  updateAnnotation(index: number, text: string): void;
  deleteAnnotation(index: number): void;
}

/** Return a copy of `doc` with cell (gridIndex, cellIndex) replaced by the
 * result of `update`, cloning only the path that changed. */
function withCell(doc: Cwd, sel: Selection, update: (cell: Cell) => Cell): Cwd {
  const grids = doc.grids.map((grid, gi) => {
    if (gi !== sel.gridIndex) return grid;
    const cells = grid.cells.map((cell, ci) => (ci === sel.cellIndex ? update(cell) : cell));
    return { ...grid, cells } as Grid;
  });
  return { ...doc, grids };
}

function cellAt(doc: Cwd, sel: Selection): Cell | null {
  return doc.grids[sel.gridIndex]?.cells[sel.cellIndex] ?? null;
}

const cleared = (cell: Cell): Cell => ({ ...cell, kind: "empty", letter: null });
const normalizeChar = (ch: string): string => (/[a-z]/i.test(ch) ? ch.toUpperCase() : ch);

export const useEditor = create<EditorState>((set, get) => ({
  doc: null,
  image: null,
  fileName: null,
  selection: null,
  mode: "normal",
  highlight: DEFAULT_HIGHLIGHT_BGR,
  dirty: false,

  loadDocument(doc, image, fileName) {
    set({ doc, image, fileName, selection: null, mode: "normal", dirty: false });
  },

  closeDocument() {
    set({ doc: null, image: null, fileName: null, selection: null, mode: "normal", dirty: false });
  },

  selectCell(gridIndex, cellIndex) {
    set({ selection: { gridIndex, cellIndex }, mode: "normal" });
  },

  clearSelection() {
    set({ selection: null, mode: "normal" });
  },

  enterMultiEntry(gridIndex, cellIndex) {
    const doc = get().doc;
    if (!doc) return;
    const cell = doc.grids[gridIndex]?.cells[cellIndex];
    if (!cell || cell.kind === "block") return;
    set({ selection: { gridIndex, cellIndex }, mode: "multiEntry" });
  },

  exitMultiEntry() {
    if (get().mode === "multiEntry") set({ mode: "normal" });
  },

  typeChar(ch) {
    const { doc, selection, mode } = get();
    if (!doc || !selection) return;
    const cell = cellAt(doc, selection);
    if (!cell || cell.kind === "block") return;
    const char = normalizeChar(ch);

    if (mode === "multiEntry") {
      set({
        doc: withCell(doc, selection, (c) => ({
          ...c,
          kind: "letter",
          letter: (c.letter ?? "") + char,
        })),
        dirty: true,
      });
      return;
    }

    const next = withCell(doc, selection, (c) => ({ ...c, kind: "letter", letter: char }));
    const grid = next.grids[selection.gridIndex]!;
    const advance = nextFillable(grid, selection.cellIndex);
    set({
      doc: next,
      dirty: true,
      selection: advance === null ? selection : { ...selection, cellIndex: advance },
    });
  },

  backspace() {
    const { doc, selection, mode } = get();
    if (!doc || !selection) return;
    const cell = cellAt(doc, selection);
    if (!cell || cell.kind === "block") return;

    if (mode === "multiEntry") {
      const trimmed = (cell.letter ?? "").slice(0, -1);
      set({
        doc: withCell(doc, selection, (c) => ({
          ...c,
          letter: trimmed === "" ? null : trimmed,
          kind: trimmed === "" ? "empty" : "letter",
        })),
        dirty: true,
      });
      return;
    }

    // Normal mode: clear this cell, or if already empty, step back and clear.
    if (cell.letter) {
      set({ doc: withCell(doc, selection, cleared), dirty: true });
      return;
    }
    const grid = doc.grids[selection.gridIndex]!;
    const prev = prevFillable(grid, selection.cellIndex);
    if (prev === null) return;
    const back: Selection = { ...selection, cellIndex: prev };
    set({ doc: withCell(doc, back, cleared), selection: back, dirty: true });
  },

  deleteCell() {
    const { doc, selection } = get();
    if (!doc || !selection) return;
    const cell = cellAt(doc, selection);
    if (!cell || cell.kind === "block") return;
    set({ doc: withCell(doc, selection, cleared), dirty: true });
  },

  move(direction) {
    const { doc, selection } = get();
    if (!doc || !selection) return;
    const grid = doc.grids[selection.gridIndex];
    if (!grid) return;
    const next = neighbor(grid, selection.cellIndex, direction);
    if (next !== null) set({ selection: { ...selection, cellIndex: next }, mode: "normal" });
  },

  toggleHighlight() {
    const { doc, selection, highlight } = get();
    if (!doc || !selection) return;
    const cell = cellAt(doc, selection);
    if (!cell || cell.kind === "block") return;
    set({
      doc: withCell(doc, selection, (c) => ({
        ...c,
        background: c.background ? null : ([...highlight] as Bgr),
      })),
      dirty: true,
    });
  },

  setHighlight(bgr) {
    set({ highlight: bgr });
  },

  addAnnotation(x, y, text) {
    const doc = get().doc;
    if (!doc) return -1;
    const annotations: Annotation[] = [...doc.annotations, [x, y, text]];
    set({ doc: { ...doc, annotations }, dirty: true });
    return annotations.length - 1;
  },

  updateAnnotation(index, text) {
    const doc = get().doc;
    if (!doc) return;
    const annotations = doc.annotations.map((a, i): Annotation =>
      i === index ? [a[0], a[1], text] : a,
    );
    set({ doc: { ...doc, annotations }, dirty: true });
  },

  deleteAnnotation(index) {
    const doc = get().doc;
    if (!doc) return;
    const annotations = doc.annotations.filter((_, i) => i !== index);
    set({ doc: { ...doc, annotations }, dirty: true });
  },
}));
