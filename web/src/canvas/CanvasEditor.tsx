/** The interactive editing surface: a single canvas that draws the document and
 * translates pointer/keyboard input into store mutations (per web/editor.md). */

import { useCallback, useEffect, useRef, useState } from "react";
import { useEditor } from "../state/store.ts";
import { renderScene } from "./render.ts";
import { canvasToNorm, computeViewport, normToCanvas, type Viewport } from "./viewport.ts";
import { annotationFontSize, hitTestAnnotation, hitTestCell } from "./hitTest.ts";
import { AnnotationEditor, type AnnotationEdit } from "../ui/AnnotationEditor.tsx";
import { ContextMenu, type ContextMenuState } from "../ui/ContextMenu.tsx";
import { hexToBgr } from "../model/color.ts";
import { saveCwd, exportImage } from "../lib/files.ts";
import type { Direction } from "../model/grid.ts";

const ARROW_DIRECTIONS: Record<string, Direction> = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
};

export function CanvasEditor() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const vpRef = useRef<Viewport | null>(null);
  const colorInputRef = useRef<HTMLInputElement>(null);

  const doc = useEditor((s) => s.doc);
  const image = useEditor((s) => s.image);
  const selection = useEditor((s) => s.selection);
  const mode = useEditor((s) => s.mode);

  const [edit, setEdit] = useState<AnnotationEdit | null>(null);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  // Mirror `edit` so commit/cancel can read it without stale closures and
  // without mutating the store inside a setState updater.
  const editRef = useRef<AnnotationEdit | null>(null);
  editRef.current = edit;

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

    const { doc: d, image: img, selection: sel, mode: m } = useEditor.getState();
    if (!d || !img) {
      vpRef.current = null;
      return;
    }
    const vp = computeViewport(cssW, cssH, img.width, img.height);
    vpRef.current = vp;
    renderScene(ctx, {
      doc: d,
      viewport: vp,
      image: img.element,
      selection: sel,
      mode: m,
      showChrome: true,
    });
  }, []);

  // Redraw on any relevant state change.
  useEffect(() => {
    draw();
  }, [draw, doc, image, selection, mode, edit]);

  // Redraw on container resize (canvas fills the window).
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const ro = new ResizeObserver(() => draw());
    ro.observe(container);
    return () => ro.disconnect();
  }, [draw]);

  const commitEdit = useCallback(() => {
    const current = editRef.current;
    if (!current) return;
    const store = useEditor.getState();
    if (current.value.trim() === "") store.deleteAnnotation(current.index);
    else store.updateAnnotation(current.index, current.value);
    setEdit(null);
  }, []);

  const cancelEdit = useCallback(() => {
    const current = editRef.current;
    if (current) {
      const ann = useEditor.getState().doc?.annotations[current.index];
      // A freshly-added, still-empty annotation is discarded on cancel.
      if (ann && ann[2] === "") useEditor.getState().deleteAnnotation(current.index);
    }
    setEdit(null);
  }, []);

  const startEditingAnnotation = useCallback((index: number) => {
    const vp = vpRef.current;
    const doc2 = useEditor.getState().doc;
    if (!vp || !doc2) return;
    const ann = doc2.annotations[index];
    if (!ann) return;
    const [x, y] = normToCanvas(vp, [ann[0], ann[1]]);
    setEdit({ index, x, y, value: ann[2], fontSize: annotationFontSize(vp) });
  }, []);

  const onClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const vp = vpRef.current;
      const ctx = canvasRef.current?.getContext("2d");
      const store = useEditor.getState();
      if (!vp || !ctx || !store.doc) return;
      const cx = e.nativeEvent.offsetX;
      const cy = e.nativeEvent.offsetY;

      const annIndex = hitTestAnnotation(ctx, store.doc, vp, cx, cy);
      if (annIndex !== null) {
        startEditingAnnotation(annIndex);
        return;
      }
      const cell = hitTestCell(store.doc, vp, cx, cy);
      if (cell) store.selectCell(cell.gridIndex, cell.cellIndex);
      else store.clearSelection();
    },
    [startEditingAnnotation],
  );

  const onDoubleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const vp = vpRef.current;
    const store = useEditor.getState();
    if (!vp || !store.doc) return;
    const cx = e.nativeEvent.offsetX;
    const cy = e.nativeEvent.offsetY;

    const cell = hitTestCell(store.doc, vp, cx, cy);
    if (cell) {
      store.enterMultiEntry(cell.gridIndex, cell.cellIndex);
      return;
    }
    // Empty space: add a new annotation here and edit it immediately.
    const [nx, ny] = canvasToNorm(vp, cx, cy);
    const index = store.addAnnotation(nx, ny, "");
    setEdit({ index, x: cx, y: cy, value: "", fontSize: annotationFontSize(vp) });
  }, []);

  const onContextMenu = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const vp = vpRef.current;
    const ctx = canvasRef.current?.getContext("2d");
    const store = useEditor.getState();
    if (!vp || !ctx || !store.doc) return;
    const annIndex = hitTestAnnotation(ctx, store.doc, vp, e.nativeEvent.offsetX, e.nativeEvent.offsetY);
    if (annIndex === null) return;
    e.preventDefault();
    setMenu({
      x: e.nativeEvent.offsetX,
      y: e.nativeEvent.offsetY,
      onDelete: () => store.deleteAnnotation(annIndex),
    });
  }, []);

  // Global keyboard handling while a document is open (and not editing text).
  // Depends only on whether a document exists, so it doesn't re-subscribe on
  // every edit; all live state is read via getState() inside the handler.
  const hasDoc = doc !== null;
  useEffect(() => {
    if (!hasDoc) return;
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;
      const store = useEditor.getState();
      if (!store.doc) return;

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

      if (e.key in ARROW_DIRECTIONS) {
        e.preventDefault();
        store.move(ARROW_DIRECTIONS[e.key]!);
        return;
      }
      switch (e.key) {
        case "Escape":
          if (store.mode === "multiEntry") store.exitMultiEntry();
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
          store.deleteCell();
          return;
      }
      // A single printable character fills the cell.
      if (e.key.length === 1 && !/\s/.test(e.key)) {
        store.typeChar(e.key);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [hasDoc]);

  return (
    <div ref={containerRef} className="canvas-wrap">
      <canvas
        ref={canvasRef}
        className="editor-canvas"
        onClick={onClick}
        onDoubleClick={onDoubleClick}
        onContextMenu={onContextMenu}
      />
      {edit && (
        <AnnotationEditor
          edit={edit}
          onChange={(value) => setEdit((cur) => (cur ? { ...cur, value } : cur))}
          onCommit={commitEdit}
          onCancel={cancelEdit}
        />
      )}
      {menu && <ContextMenu menu={menu} onClose={() => setMenu(null)} />}
      <input
        ref={colorInputRef}
        type="color"
        className="hidden-color-input"
        onChange={(e) => useEditor.getState().setHighlight(hexToBgr(e.target.value))}
      />
    </div>
  );
}
