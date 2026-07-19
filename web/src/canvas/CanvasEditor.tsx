/** The interactive editing surface: a single canvas that draws the document and
 * translates pointer/keyboard input into store mutations (per web/editor.md).
 *
 * Pointer behaviour is dispatched by the active tool: `select` handles cell
 * entry/selection and annotation move/edit; `text`/`line`/`curve` create
 * annotations; `eraser` deletes them. An in-progress drawing or drag is kept in
 * refs and drawn as a live `draft` preview, then committed once (one undo step).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useEditor, type Selection } from "../state/store.ts";
import { renderScene } from "./render.ts";
import {
  canvasToNorm,
  computeViewport,
  computeViewportForRegion,
  normToCanvas,
  type Viewport,
} from "./viewport.ts";
import { hitTestCell } from "./hitTest.ts";
import {
  hitTestAnnotations,
  hitTestHandle,
  moveAnnotationBy,
  moveAnnotationHandle,
} from "../annotations/registry.ts";
import { annotationFontSize } from "../annotations/sizes.ts";
import { createCurve, createLine, createText, type Annotation } from "../annotations/types.ts";
import { AnnotationEditor, type AnnotationEdit } from "../ui/AnnotationEditor.tsx";
import { bgrToCss, hexToBgr, persistedColor, type Bgr } from "../model/color.ts";
import { saveCwd, exportImage } from "../lib/files.ts";
import { boundsOf, type Point } from "../model/geometry.ts";
import { boundingPolygon, type Direction } from "../model/grid.ts";

const ARROW_DIRECTIONS: Record<string, Direction> = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
};

/** Placeholder id for the preview annotation (never persisted). */
const DRAFT_ID = "__draft__";
/** Canvas-pixel move past which a pointer press counts as a drag, not a click. */
const DRAG_THRESHOLD = 3;

const CURSOR: Record<string, string> = {
  select: "default",
  text: "text",
  line: "crosshair",
  curve: "crosshair",
  eraser: "cell",
};

/** Where an open text editor writes to: a new annotation or an existing one. */
type EditTarget =
  | { kind: "new"; nx: number; ny: number; color: Bgr | null }
  | { kind: "existing"; id: string };

/** An in-progress pointer drag (select/line tools). */
type Gesture =
  | { kind: "line"; start: Point; color: Bgr | null }
  | { kind: "move"; id: string; original: Annotation; startNorm: Point; moved: boolean }
  | { kind: "handle"; id: string; handleId: string; original: Annotation; moved: boolean }
  | { kind: "marquee"; startNorm: Point; startCanvas: Point; cellHit: Selection | null; moved: boolean };

export function CanvasEditor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const vpRef = useRef<Viewport | null>(null);
  const colorInputRef = useRef<HTMLInputElement>(null);

  const doc = useEditor((s) => s.doc);
  const image = useEditor((s) => s.image);
  const selection = useEditor((s) => s.selection);
  const mode = useEditor((s) => s.mode);
  const tool = useEditor((s) => s.tool);
  const selectedAnnotationId = useEditor((s) => s.selectedAnnotationId);
  const selectedCells = useEditor((s) => s.selectedCells);
  const zoomToGrid = useEditor((s) => s.zoomToGrid);

  const [edit, setEdit] = useState<AnnotationEdit | null>(null);
  const editRef = useRef<AnnotationEdit | null>(null);
  editRef.current = edit;
  const editTargetRef = useRef<EditTarget | null>(null);

  // In-progress drawing state (refs so pointer moves don't churn React state).
  const gestureRef = useRef<Gesture | null>(null);
  const curveRef = useRef<Point[] | null>(null);
  const draftRef = useRef<Annotation | null>(null);
  const hiddenIdRef = useRef<string | null>(null);
  // Live marquee rectangle [startNorm, currentNorm] while dragging a selection box.
  const marqueeRef = useRef<[Point, Point] | null>(null);

  // (Re)size the canvas to its container and draw the current scene.
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const cssW = container.clientWidth;
    const cssH = container.clientHeight;
    canvas.width = Math.max(1, Math.round(cssW * dpr));
    canvas.height = Math.max(1, Math.round(cssH * dpr));
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    const s = useEditor.getState();
    if (!s.doc || !s.image) {
      vpRef.current = null;
      return;
    }
    const grid = s.selection ? s.doc.grids[s.selection.gridIndex] : undefined;
    const vp =
      s.zoomToGrid && grid
        ? computeViewportForRegion(
            cssW,
            cssH,
            s.image.width,
            s.image.height,
            boundsOf(boundingPolygon(grid)),
          )
        : computeViewport(cssW, cssH, s.image.width, s.image.height);
    vpRef.current = vp;
    renderScene(ctx, {
      doc: s.doc,
      viewport: vp,
      image: s.image.element,
      selection: s.selection,
      selectedCells: s.selectedCells,
      mode: s.mode,
      showChrome: true,
      tool: s.tool,
      selectedAnnotationId: s.selectedAnnotationId,
      draft: draftRef.current,
      hiddenAnnotationId: hiddenIdRef.current,
      marquee: marqueeRef.current,
    });
  }, []);

  // Redraw on any relevant state change.
  useEffect(() => {
    draw();
  }, [draw, doc, image, selection, selectedCells, mode, tool, selectedAnnotationId, zoomToGrid, edit]);

  // Redraw on container resize (canvas fills the window).
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const ro = new ResizeObserver(() => draw());
    ro.observe(container);
    return () => ro.disconnect();
  }, [draw]);

  // Cancel any in-progress drawing when the tool changes.
  useEffect(() => {
    gestureRef.current = null;
    curveRef.current = null;
    draftRef.current = null;
    hiddenIdRef.current = null;
    marqueeRef.current = null;
    draw();
  }, [tool, draw]);

  const clearDraft = useCallback(() => {
    gestureRef.current = null;
    draftRef.current = null;
    hiddenIdRef.current = null;
  }, []);

  const openTextEditor = useCallback(
    (canvasX: number, canvasY: number, value: string, color: Bgr | null, target: EditTarget) => {
      const vp = vpRef.current;
      if (!vp) return;
      editTargetRef.current = target;
      if (target.kind === "existing") hiddenIdRef.current = target.id;
      setEdit({
        x: canvasX,
        y: canvasY,
        value,
        fontSize: annotationFontSize(vp),
        color: color ? bgrToCss(color) : "#000000",
      });
    },
    [],
  );

  const commitEdit = useCallback(() => {
    const target = editTargetRef.current;
    const value = editRef.current?.value ?? "";
    const store = useEditor.getState();
    if (target?.kind === "new") {
      if (value.trim() !== "") store.addAnnotation(createText(target.nx, target.ny, value, target.color));
    } else if (target?.kind === "existing") {
      const ann = store.doc?.annotations.find((a) => a.id === target.id);
      if (ann && ann.type === "text") {
        if (value.trim() === "") store.deleteAnnotation(target.id);
        else store.updateAnnotation(target.id, { ...ann, text: value });
      }
    }
    editTargetRef.current = null;
    hiddenIdRef.current = null;
    setEdit(null);
  }, []);

  const cancelEdit = useCallback(() => {
    editTargetRef.current = null;
    hiddenIdRef.current = null;
    setEdit(null);
  }, []);

  const finishCurve = useCallback(() => {
    const points = curveRef.current;
    curveRef.current = null;
    draftRef.current = null;
    if (points && points.length >= 2) {
      const color = persistedColor(useEditor.getState().textColor);
      useEditor.getState().addAnnotation(createCurve(points, color));
    }
    draw();
  }, [draw]);

  const cancelCurve = useCallback(() => {
    curveRef.current = null;
    draftRef.current = null;
    draw();
  }, [draw]);

  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const vp = vpRef.current;
      const ctx = canvasRef.current?.getContext("2d");
      const store = useEditor.getState();
      if (!vp || !ctx || !store.doc) return;
      if (edit) commitEdit();
      const cx = e.nativeEvent.offsetX;
      const cy = e.nativeEvent.offsetY;
      const norm = canvasToNorm(vp, cx, cy);

      switch (store.tool) {
        case "select": {
          // A handle of the already-selected annotation?
          if (store.selectedAnnotationId) {
            const sel = store.doc.annotations.find((a) => a.id === store.selectedAnnotationId);
            const hid = sel && hitTestHandle(vp, sel, cx, cy);
            if (sel && hid) {
              canvasRef.current?.setPointerCapture(e.pointerId);
              gestureRef.current = {
                kind: "handle",
                id: sel.id,
                handleId: hid,
                original: sel,
                moved: false,
              };
              return;
            }
          }
          // An annotation body? Select it and start a potential move.
          const annId = hitTestAnnotations(ctx, store.doc, vp, cx, cy);
          if (annId) {
            const ann = store.doc.annotations.find((a) => a.id === annId)!;
            store.selectAnnotation(annId);
            canvasRef.current?.setPointerCapture(e.pointerId);
            gestureRef.current = {
              kind: "move",
              id: annId,
              original: ann,
              startNorm: norm,
              moved: false,
            };
            return;
          }
          // Otherwise a cell or empty space: begin a potential marquee. A press
          // with no drag falls back to a plain click (select the cell / clear).
          const cell = hitTestCell(store.doc, vp, cx, cy);
          canvasRef.current?.setPointerCapture(e.pointerId);
          gestureRef.current = {
            kind: "marquee",
            startNorm: norm,
            startCanvas: [cx, cy],
            cellHit: cell,
            moved: false,
          };
          return;
        }
        case "text": {
          const color = persistedColor(store.textColor);
          openTextEditor(cx, cy, "", color, { kind: "new", nx: norm[0], ny: norm[1], color });
          return;
        }
        case "line": {
          const color = persistedColor(store.textColor);
          canvasRef.current?.setPointerCapture(e.pointerId);
          gestureRef.current = { kind: "line", start: norm, color };
          draftRef.current = { id: DRAFT_ID, type: "line", color, points: [norm, norm] };
          draw();
          return;
        }
        case "curve": {
          const color = persistedColor(store.textColor);
          if (curveRef.current) curveRef.current.push(norm);
          else curveRef.current = [norm];
          draftRef.current = { id: DRAFT_ID, type: "curve", color, points: [...curveRef.current] };
          draw();
          return;
        }
        case "eraser": {
          const annId = hitTestAnnotations(ctx, store.doc, vp, cx, cy);
          if (annId) store.deleteAnnotation(annId);
          return;
        }
      }
    },
    [edit, commitEdit, openTextEditor, draw],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const vp = vpRef.current;
      if (!vp) return;
      const cx = e.nativeEvent.offsetX;
      const cy = e.nativeEvent.offsetY;
      const norm = canvasToNorm(vp, cx, cy);
      const g = gestureRef.current;

      if (g) {
        if (g.kind === "marquee") {
          if (!g.moved && Math.hypot(cx - g.startCanvas[0], cy - g.startCanvas[1]) > DRAG_THRESHOLD) {
            g.moved = true;
          }
          if (g.moved) {
            marqueeRef.current = [g.startNorm, norm];
            draw();
          }
          return;
        }
        if (g.kind === "line") {
          draftRef.current = { id: DRAFT_ID, type: "line", color: g.color, points: [g.start, norm] };
        } else if (g.kind === "move") {
          if (Math.hypot(cx - normToCanvas(vp, g.startNorm)[0], cy - normToCanvas(vp, g.startNorm)[1]) > DRAG_THRESHOLD) {
            g.moved = true;
          }
          draftRef.current = moveAnnotationBy(g.original, norm[0] - g.startNorm[0], norm[1] - g.startNorm[1]);
          hiddenIdRef.current = g.id;
        } else {
          // handle drag
          if (!g.moved) g.moved = true;
          draftRef.current = moveAnnotationHandle(g.original, g.handleId, norm);
          hiddenIdRef.current = g.id;
        }
        draw();
        return;
      }

      // Curve tool: preview a rubber-band segment to the cursor.
      if (curveRef.current) {
        const store = useEditor.getState();
        draftRef.current = {
          id: DRAFT_ID,
          type: "curve",
          color: persistedColor(store.textColor),
          points: [...curveRef.current, norm],
        };
        draw();
      }
    },
    [draw],
  );

  const onPointerUp = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const vp = vpRef.current;
      const store = useEditor.getState();
      const g = gestureRef.current;
      canvasRef.current?.releasePointerCapture?.(e.pointerId);
      if (!vp || !g) return;

      if (g.kind === "marquee") {
        if (g.moved && marqueeRef.current) {
          const [a, b] = marqueeRef.current;
          store.selectCellsInRect([a[0], a[1], b[0], b[1]]);
        } else if (g.cellHit) {
          store.selectCell(g.cellHit.gridIndex, g.cellHit.cellIndex);
        } else {
          store.clearSelection();
        }
        gestureRef.current = null;
        marqueeRef.current = null;
        draw();
        return;
      }

      if (g.kind === "line") {
        const draft = draftRef.current;
        const [p0, p1] = draft && draft.type === "line" ? draft.points : [g.start, g.start];
        const [c0x, c0y] = normToCanvas(vp, p0);
        const [c1x, c1y] = normToCanvas(vp, p1);
        if (Math.hypot(c1x - c0x, c1y - c0y) > DRAG_THRESHOLD) {
          store.addAnnotation(createLine(p0, p1, g.color));
        }
        clearDraft();
        draw();
        return;
      }

      if (g.kind === "move") {
        if (g.moved && draftRef.current) {
          store.updateAnnotation(g.id, draftRef.current);
        } else if (g.original.type === "text") {
          // A click without a drag on a text annotation: edit it.
          const [x, y] = normToCanvas(vp, [g.original.x, g.original.y]);
          openTextEditor(x, y, g.original.text, g.original.color, { kind: "existing", id: g.id });
        }
        clearDraft();
        draw();
        return;
      }

      // handle drag
      if (g.moved && draftRef.current) store.updateAnnotation(g.id, draftRef.current);
      clearDraft();
      draw();
    },
    [clearDraft, draw, openTextEditor],
  );

  const onDoubleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const vp = vpRef.current;
      const ctx = canvasRef.current?.getContext("2d");
      const store = useEditor.getState();
      if (!vp || !ctx || !store.doc) return;
      const cx = e.nativeEvent.offsetX;
      const cy = e.nativeEvent.offsetY;

      if (store.tool === "curve" && curveRef.current) {
        finishCurve();
        return;
      }
      if (store.tool !== "select") return;

      const annId = hitTestAnnotations(ctx, store.doc, vp, cx, cy);
      if (annId) {
        const ann = store.doc.annotations.find((a) => a.id === annId);
        if (ann && ann.type === "text") {
          store.selectAnnotation(annId);
          const [x, y] = normToCanvas(vp, [ann.x, ann.y]);
          openTextEditor(x, y, ann.text, ann.color, { kind: "existing", id: annId });
        }
        return;
      }
      const cell = hitTestCell(store.doc, vp, cx, cy);
      if (cell) store.enterMultiEntry(cell.gridIndex, cell.cellIndex);
    },
    [finishCurve, openTextEditor],
  );

  // Global keyboard handling while a document is open (and not editing text).
  const hasDoc = doc !== null;
  useEffect(() => {
    if (!hasDoc) return;
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;
      const store = useEditor.getState();
      if (!store.doc) return;

      // Undo / redo (any tool).
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) store.redo();
        else store.undo();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        store.redo();
        return;
      }

      // File shortcuts.
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (e.shiftKey) {
          if (store.image) exportImage(store.doc, store.image.element, "png", store.fileName);
        } else {
          saveCwd(store.doc, store.fileName);
        }
        return;
      }

      // Highlighting.
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "h") {
        e.preventDefault();
        if (e.shiftKey) colorInputRef.current?.click();
        else store.toggleHighlight();
        return;
      }

      if (e.ctrlKey || e.metaKey || e.altKey) return;

      // Finish / cancel an in-progress curve.
      if (curveRef.current) {
        if (e.key === "Enter") {
          e.preventDefault();
          finishCurve();
          return;
        }
        if (e.key === "Escape") {
          e.preventDefault();
          cancelCurve();
          return;
        }
      }

      // Delete the selected annotation.
      if ((e.key === "Delete" || e.key === "Backspace") && store.selectedAnnotationId && !store.selection) {
        e.preventDefault();
        store.deleteAnnotation(store.selectedAnnotationId);
        return;
      }

      // The rest is cell entry / navigation: select tool only.
      if (store.tool !== "select") return;

      if (e.key in ARROW_DIRECTIONS) {
        e.preventDefault();
        if (e.shiftKey) store.extendSelection(ARROW_DIRECTIONS[e.key]!);
        else store.move(ARROW_DIRECTIONS[e.key]!);
        return;
      }
      switch (e.key) {
        case "Escape":
          if (store.mode === "multiEntry") store.exitMultiEntry();
          else if (store.selectedAnnotationId) store.selectAnnotation(null);
          else store.clearSelection();
          return;
        case "Enter":
          if (store.mode === "multiEntry") store.exitMultiEntry();
          return;
        case "Backspace":
          e.preventDefault();
          store.backspace();
          return;
        case "Delete":
          e.preventDefault();
          store.deleteCell();
          return;
      }
      if (e.key.length === 1 && !/\s/.test(e.key)) {
        store.typeChar(e.key);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [hasDoc, finishCurve, cancelCurve]);

  return (
    <div ref={containerRef} className="canvas-wrap">
      <canvas
        ref={canvasRef}
        className="editor-canvas"
        style={{ cursor: CURSOR[tool] ?? "default" }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onDoubleClick={onDoubleClick}
        onContextMenu={(e) => e.preventDefault()}
      />
      {edit && (
        <AnnotationEditor
          edit={edit}
          onChange={(value) => setEdit((cur) => (cur ? { ...cur, value } : cur))}
          onCommit={commitEdit}
          onCancel={cancelEdit}
        />
      )}
      <input
        ref={colorInputRef}
        type="color"
        className="hidden-color-input"
        onChange={(e) => useEditor.getState().setHighlight(hexToBgr(e.target.value))}
      />
    </div>
  );
}
