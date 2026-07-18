/** Editor state: the loaded document plus the active tool, selection, mode,
 * highlight colour, annotation selection and an undo/redo history — and the
 * mutations behind every editor.md interaction. Kept framework-light (a zustand
 * store) so the canvas can subscribe and redraw imperatively.
 */

import { create } from "zustand";
import type { Cell, Cwd, Grid } from "../model/cwd.ts";
import type { Annotation } from "../annotations/types.ts";
import { neighbor, nextFillable, prevFillable, type Direction } from "../model/grid.ts";
import { DEFAULT_HIGHLIGHT_BGR, DEFAULT_TEXT_BGR, persistedColor, type Bgr } from "../model/color.ts";

export interface Selection {
  gridIndex: number;
  cellIndex: number;
}

export type Mode = "normal" | "multiEntry";

/** The active pointer tool. `select` is the default (cell entry & selection);
 * the others create/erase annotations. */
export type Tool = "select" | "text" | "line" | "curve" | "eraser";

interface LoadedImage {
  element: HTMLImageElement;
  width: number;
  height: number;
}

/** How many past states undo can step back through. */
const HISTORY_CAP = 100;

export interface EditorState {
  doc: Cwd | null;
  image: LoadedImage | null;
  fileName: string | null;
  tool: Tool;
  selection: Selection | null;
  /** The selected annotation (for moving / handle editing), by id. */
  selectedAnnotationId: string | null;
  mode: Mode;
  highlight: Bgr;
  /** Colour applied to newly typed letters and new annotations (default black). */
  textColor: Bgr;
  dirty: boolean;
  /** Undo/redo stacks of whole-document snapshots (cheap: immutable + shared). */
  past: Cwd[];
  future: Cwd[];

  loadDocument(doc: Cwd, image: LoadedImage, fileName: string | null): void;
  closeDocument(): void;

  setTool(tool: Tool): void;

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
  setTextColor(bgr: Bgr): void;

  selectAnnotation(id: string | null): void;
  addAnnotation(a: Annotation): void;
  updateAnnotation(id: string, next: Annotation): void;
  deleteAnnotation(id: string): void;

  undo(): void;
  redo(): void;
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

export const useEditor = create<EditorState>((set, get) => {
  /** The `set` payload that commits `nextDoc` as an undoable change: pushes the
   * current doc onto the history and clears the redo stack. Spread into a `set`
   * call alongside any selection/mode fields the same action changes. */
  const commit = (nextDoc: Cwd): Partial<EditorState> => {
    const { doc, past } = get();
    return {
      doc: nextDoc,
      past: doc ? [...past, doc].slice(-HISTORY_CAP) : past,
      future: [],
      dirty: true,
    };
  };

  return {
    doc: null,
    image: null,
    fileName: null,
    tool: "select",
    selection: null,
    selectedAnnotationId: null,
    mode: "normal",
    highlight: DEFAULT_HIGHLIGHT_BGR,
    textColor: DEFAULT_TEXT_BGR,
    dirty: false,
    past: [],
    future: [],

    loadDocument(doc, image, fileName) {
      set({
        doc,
        image,
        fileName,
        selection: null,
        selectedAnnotationId: null,
        mode: "normal",
        dirty: false,
        past: [],
        future: [],
      });
    },

    closeDocument() {
      set({
        doc: null,
        image: null,
        fileName: null,
        selection: null,
        selectedAnnotationId: null,
        mode: "normal",
        dirty: false,
        past: [],
        future: [],
      });
    },

    setTool(tool) {
      set({ tool, selectedAnnotationId: null });
    },

    selectCell(gridIndex, cellIndex) {
      set({ selection: { gridIndex, cellIndex }, mode: "normal", selectedAnnotationId: null });
    },

    clearSelection() {
      set({ selection: null, mode: "normal", selectedAnnotationId: null });
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
      const { doc, selection, mode, textColor } = get();
      if (!doc || !selection) return;
      const cell = cellAt(doc, selection);
      if (!cell || cell.kind === "block") return;
      const char = normalizeChar(ch);
      const color = persistedColor(textColor);

      if (mode === "multiEntry") {
        set(
          commit(
            withCell(doc, selection, (c) => ({
              ...c,
              kind: "letter",
              letter: (c.letter ?? "") + char,
              textColor: color,
            })),
          ),
        );
        return;
      }

      const next = withCell(doc, selection, (c) => ({
        ...c,
        kind: "letter",
        letter: char,
        textColor: color,
      }));
      const grid = next.grids[selection.gridIndex]!;
      const advance = nextFillable(grid, selection.cellIndex);
      set({
        ...commit(next),
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
        set(
          commit(
            withCell(doc, selection, (c) => ({
              ...c,
              letter: trimmed === "" ? null : trimmed,
              kind: trimmed === "" ? "empty" : "letter",
            })),
          ),
        );
        return;
      }

      // Normal mode: clear this cell, or if already empty, step back and clear.
      if (cell.letter) {
        set(commit(withCell(doc, selection, cleared)));
        return;
      }
      const grid = doc.grids[selection.gridIndex]!;
      const prev = prevFillable(grid, selection.cellIndex);
      if (prev === null) return;
      const back: Selection = { ...selection, cellIndex: prev };
      set({ ...commit(withCell(doc, back, cleared)), selection: back });
    },

    deleteCell() {
      const { doc, selection } = get();
      if (!doc || !selection) return;
      const cell = cellAt(doc, selection);
      if (!cell || cell.kind === "block") return;
      set(commit(withCell(doc, selection, cleared)));
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
      set(
        commit(
          withCell(doc, selection, (c) => ({
            ...c,
            background: c.background ? null : ([...highlight] as Bgr),
          })),
        ),
      );
    },

    setHighlight(bgr) {
      set({ highlight: bgr });
    },

    setTextColor(bgr) {
      set({ textColor: bgr });
    },

    selectAnnotation(id) {
      set({ selectedAnnotationId: id });
    },

    addAnnotation(a) {
      const doc = get().doc;
      if (!doc) return;
      set(commit({ ...doc, annotations: [...doc.annotations, a] }));
    },

    updateAnnotation(id, next) {
      const doc = get().doc;
      if (!doc) return;
      const annotations = doc.annotations.map((a) => (a.id === id ? next : a));
      set(commit({ ...doc, annotations }));
    },

    deleteAnnotation(id) {
      const doc = get().doc;
      if (!doc) return;
      const annotations = doc.annotations.filter((a) => a.id !== id);
      const selectedAnnotationId =
        get().selectedAnnotationId === id ? null : get().selectedAnnotationId;
      set({ ...commit({ ...doc, annotations }), selectedAnnotationId });
    },

    undo() {
      const { past, doc, future } = get();
      if (past.length === 0 || !doc) return;
      const prev = past[past.length - 1]!;
      set({
        doc: prev,
        past: past.slice(0, -1),
        future: [doc, ...future],
        dirty: true,
        selection: null,
        selectedAnnotationId: null,
      });
    },

    redo() {
      const { future, doc, past } = get();
      if (future.length === 0 || !doc) return;
      const next = future[0]!;
      set({
        doc: next,
        future: future.slice(1),
        past: [...past, doc],
        dirty: true,
        selection: null,
        selectedAnnotationId: null,
      });
    },
  };
});
