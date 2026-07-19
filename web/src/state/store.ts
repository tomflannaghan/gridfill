/** Editor state: the loaded document plus the active tool, selection, mode,
 * highlight colour, annotation selection and an undo/redo history — and the
 * mutations behind every editor.md interaction. Kept framework-light (a zustand
 * store) so the canvas can subscribe and redraw imperatively.
 */

import { create } from "zustand";
import type { Cell, Cwd, Grid } from "../model/cwd.ts";
import type { Annotation } from "../annotations/types.ts";
import { neighbor, nextFillable, prevFillable, type Direction } from "../model/grid.ts";
import { cellsInRect } from "../canvas/hitTest.ts";
import { DEFAULT_HIGHLIGHT_BGR, DEFAULT_TEXT_BGR, persistedColour, type Bgr } from "../model/colour.ts";

export interface Selection {
  gridIndex: number;
  cellIndex: number;
}

const selectionKey = (s: Selection): string => `${s.gridIndex}:${s.cellIndex}`;

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
  /** Additional cells in a multi-cell selection (Shift+Arrow or marquee). Empty
   * means only the single active `selection` (if any) is selected. */
  selectedCells: Selection[];
  /** The selected annotation (for moving / handle editing), by id. */
  selectedAnnotationId: string | null;
  mode: Mode;
  highlight: Bgr;
  /** Colour applied to newly typed letters and new annotations (default black). */
  textColour: Bgr;
  /** When true, the view zooms to fit the grid of the current selection. A view
   * preference (not part of the document, not undoable). */
  zoomToGrid: boolean;
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

  /** Extend the multi-cell selection by moving the active cell in `direction`,
   * accumulating each visited cell (Shift+Arrow). */
  extendSelection(direction: Direction): void;
  /** Select every cell with a vertex inside the normalized rectangle (marquee). */
  selectCellsInRect(rect: [number, number, number, number]): void;

  typeChar(ch: string): void;
  backspace(): void;
  deleteCell(): void;
  move(direction: Direction): void;

  toggleHighlight(): void;
  /** Apply the current highlight colour as the background of every selected cell. */
  applyHighlightToSelection(): void;
  /** Apply the current text colour to every selected cell's letter. */
  applyTextColourToSelection(): void;
  setHighlight(bgr: Bgr): void;
  setTextColour(bgr: Bgr): void;
  setZoomToGrid(on: boolean): void;

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

/** Return a copy of `doc` with every cell in `targets` replaced by the result of
 * `update`, cloning only the grids/cells that changed. `block` cells are left
 * untouched (colours don't apply to them). */
function withCells(doc: Cwd, targets: Selection[], update: (cell: Cell) => Cell): Cwd {
  const byGrid = new Map<number, Set<number>>();
  for (const t of targets) {
    if (!byGrid.has(t.gridIndex)) byGrid.set(t.gridIndex, new Set());
    byGrid.get(t.gridIndex)!.add(t.cellIndex);
  }
  const grids = doc.grids.map((grid, gi) => {
    const indices = byGrid.get(gi);
    if (!indices) return grid;
    const cells = grid.cells.map((cell, ci) =>
      indices.has(ci) && cell.kind !== "block" ? update(cell) : cell,
    );
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

  /** The cells an apply-colour action targets: the multi-cell selection, or the
   * single active cell when there's no multi-selection. */
  const selectionTargets = (): Selection[] => {
    const { selection, selectedCells } = get();
    if (selectedCells.length) return selectedCells;
    return selection ? [selection] : [];
  };

  return {
    doc: null,
    image: null,
    fileName: null,
    tool: "select",
    selection: null,
    selectedCells: [],
    selectedAnnotationId: null,
    mode: "normal",
    highlight: DEFAULT_HIGHLIGHT_BGR,
    textColour: DEFAULT_TEXT_BGR,
    zoomToGrid: true,
    dirty: false,
    past: [],
    future: [],

    loadDocument(doc, image, fileName) {
      set({
        doc,
        image,
        fileName,
        selection: null,
        selectedCells: [],
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
        selectedCells: [],
        selectedAnnotationId: null,
        mode: "normal",
        dirty: false,
        past: [],
        future: [],
      });
    },

    setTool(tool) {
      set({ tool, selectedCells: [], selectedAnnotationId: null });
    },

    selectCell(gridIndex, cellIndex) {
      set({
        selection: { gridIndex, cellIndex },
        selectedCells: [],
        mode: "normal",
        selectedAnnotationId: null,
      });
    },

    clearSelection() {
      set({ selection: null, selectedCells: [], mode: "normal", selectedAnnotationId: null });
    },

    enterMultiEntry(gridIndex, cellIndex) {
      const doc = get().doc;
      if (!doc) return;
      const cell = doc.grids[gridIndex]?.cells[cellIndex];
      if (!cell || cell.kind === "block") return;
      set({ selection: { gridIndex, cellIndex }, selectedCells: [], mode: "multiEntry" });
    },

    extendSelection(direction) {
      const { doc, selection, selectedCells } = get();
      if (!doc || !selection) return;
      const grid = doc.grids[selection.gridIndex];
      if (!grid) return;
      // Seed the accumulated set with the starting cell.
      const seen = new Set(selectedCells.map(selectionKey));
      const cells = selectedCells.length ? [...selectedCells] : [selection];
      if (!selectedCells.length) seen.add(selectionKey(selection));

      const next = neighbor(grid, selection.cellIndex, direction);
      if (next === null) {
        set({ selectedCells: cells, mode: "normal" });
        return;
      }
      const nextSel: Selection = { gridIndex: selection.gridIndex, cellIndex: next };
      if (!seen.has(selectionKey(nextSel))) cells.push(nextSel);
      set({ selection: nextSel, selectedCells: cells, mode: "normal" });
    },

    selectCellsInRect(rect) {
      const doc = get().doc;
      if (!doc) return;
      const cells = cellsInRect(doc, rect);
      set({
        selection: cells[0] ?? null,
        selectedCells: cells,
        mode: "normal",
        selectedAnnotationId: null,
      });
    },

    exitMultiEntry() {
      if (get().mode === "multiEntry") set({ mode: "normal" });
    },

    typeChar(ch) {
      const { doc, selection, mode, textColour } = get();
      if (!doc || !selection) return;
      const cell = cellAt(doc, selection);
      if (!cell || cell.kind === "block") return;
      const char = normalizeChar(ch);
      const colour = persistedColour(textColour);

      if (mode === "multiEntry") {
        set(
          commit(
            withCell(doc, selection, (c) => ({
              ...c,
              kind: "letter",
              letter: (c.letter ?? "") + char,
              textColour: colour,
            })),
          ),
        );
        return;
      }

      const next = withCell(doc, selection, (c) => ({
        ...c,
        kind: "letter",
        letter: char,
        textColour: colour,
      }));
      const grid = next.grids[selection.gridIndex]!;
      const advance = nextFillable(grid, selection.cellIndex);
      set({
        ...commit(next),
        selection: advance === null ? selection : { ...selection, cellIndex: advance },
        selectedCells: [],
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
      const { doc } = get();
      const targets = selectionTargets();
      if (!doc || targets.length === 0) return;
      // Clears every selected cell (single or multi); block cells are skipped.
      set(commit(withCells(doc, targets, cleared)));
    },

    move(direction) {
      const { doc, selection } = get();
      if (!doc || !selection) return;
      const grid = doc.grids[selection.gridIndex];
      if (!grid) return;
      const next = neighbor(grid, selection.cellIndex, direction);
      if (next !== null)
        set({ selection: { ...selection, cellIndex: next }, selectedCells: [], mode: "normal" });
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

    applyHighlightToSelection() {
      const { doc, highlight } = get();
      const targets = selectionTargets();
      if (!doc || targets.length === 0) return;
      set(commit(withCells(doc, targets, (c) => ({ ...c, background: [...highlight] as Bgr }))));
    },

    applyTextColourToSelection() {
      const { doc, textColour } = get();
      const targets = selectionTargets();
      if (!doc || targets.length === 0) return;
      const colour = persistedColour(textColour);
      set(commit(withCells(doc, targets, (c) => ({ ...c, textColour: colour }))));
    },

    setHighlight(bgr) {
      set({ highlight: bgr });
    },

    setTextColour(bgr) {
      set({ textColour: bgr });
    },

    setZoomToGrid(on) {
      set({ zoomToGrid: on });
    },

    selectAnnotation(id) {
      // Selecting an annotation for editing deselects any cells (they can't be
      // active at the same time); deselecting (id === null) leaves cells alone.
      if (id === null) {
        set({ selectedAnnotationId: null });
        return;
      }
      set({ selectedAnnotationId: id, selection: null, selectedCells: [], mode: "normal" });
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
      // Undo/redo only change document content, never grid structure, so the
      // current selection stays valid and is preserved (undo shouldn't deselect).
      set({
        doc: prev,
        past: past.slice(0, -1),
        future: [doc, ...future],
        dirty: true,
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
      });
    },
  };
});
