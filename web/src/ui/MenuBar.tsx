/** Top bar: File actions (Open / Save / Export) and the highlight colour. */

import { useEffect, useRef, useState } from "react";
import { useEditor } from "../state/store.ts";
import { openCwdFile, saveCwd, exportImage } from "../lib/files.ts";
import { detectFromImage } from "../lib/backend.ts";
import { bgrToHex, hexToBgr } from "../model/colour.ts";
import logoUrl from "../assets/logo.svg";

interface Props {
  onError(message: string): void;
}

/** Paintbrush glyph for the "apply colour to selection" buttons. */
const PaintbrushIcon = () => (
  <svg
    width={15}
    height={15}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M14 3l7 7-8 3-2-2z" />
    <path d="M11 11l-4 4c-1 1-3 1-3 3 0 1 1 2 3 2 2 0 2-2 3-3l4-4" />
  </svg>
);

export function MenuBar({ onError }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [detecting, setDetecting] = useState(false);
  const highlightInputRef = useRef<HTMLInputElement>(null);
  const textColourInputRef = useRef<HTMLInputElement>(null);
  const doc = useEditor((s) => s.doc);
  const fileName = useEditor((s) => s.fileName);
  const highlight = useEditor((s) => s.highlight);
  const textColour = useEditor((s) => s.textColour);
  const zoomToGrid = useEditor((s) => s.zoomToGrid);
  const selection = useEditor((s) => s.selection);
  const selectedCells = useEditor((s) => s.selectedCells);
  const selectedAnnotationId = useEditor((s) => s.selectedAnnotationId);
  const dirty = useEditor((s) => s.dirty);

  const hasSelection = selection !== null || selectedCells.length > 0;
  const hasTextColourTarget = hasSelection || selectedAnnotationId !== null;

  // Picking a colour applies it to the current selection immediately, in
  // addition to becoming the colour used for subsequent typing/annotations.
  // Listen for the native "change" event (fired once when the picker closes)
  // rather than the onChange prop below (which fires on every intermediate
  // tick while dragging inside the picker) so applying is a single undo step.
  useEffect(() => {
    const el = highlightInputRef.current;
    if (!el) return;
    const onCommit = (e: Event) => {
      const s = useEditor.getState();
      s.setHighlight(hexToBgr((e.target as HTMLInputElement).value));
      s.applyHighlightToSelection(); // no-op without a selection
    };
    el.addEventListener("change", onCommit);
    return () => el.removeEventListener("change", onCommit);
  }, []);

  useEffect(() => {
    const el = textColourInputRef.current;
    if (!el) return;
    const onCommit = (e: Event) => {
      const s = useEditor.getState();
      s.setTextColour(hexToBgr((e.target as HTMLInputElement).value));
      s.applyTextColourToSelection(); // no-op without a selection/annotation
    };
    el.addEventListener("change", onCommit);
    return () => el.removeEventListener("change", onCommit);
  }, []);

  const isCwdFile = (file: File) =>
    file.name.toLowerCase().endsWith(".cwd") || file.type === "application/json";

  const openFile = async (file: File) => {
    setDetecting(!isCwdFile(file));
    try {
      const loaded = isCwdFile(file) ? await openCwdFile(file) : await detectFromImage(file);
      useEditor
        .getState()
        .loadDocument(
          loaded.doc,
          { element: loaded.image, width: loaded.width, height: loaded.height },
          loaded.fileName,
        );
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setDetecting(false);
    }
  };

  const hasDoc = doc !== null;

  return (
    <header className="menubar">
      <span className="brand">
        <img src={logoUrl} alt="" className="brand-logo" />
        Gridfill Editor
      </span>

      <button
        type="button"
        disabled={detecting}
        onClick={() => fileInputRef.current?.click()}
        title="Open a .cwd document, or an image/PDF to detect a grid from via the gridfill backend"
      >
        {detecting ? "Loading…" : "Open…"}
      </button>
      <button type="button" disabled={!hasDoc} onClick={() => doc && saveCwd(doc, fileName)}>
        Save
      </button>
      <button
        type="button"
        disabled={!hasDoc}
        onClick={() => {
          const s = useEditor.getState();
          if (s.doc && s.image) exportImage(s.doc, s.image.element, s.fileName);
        }}
      >
        Export Image
      </button>

      <label className="color-control">
        Highlight
        <input
          ref={highlightInputRef}
          type="color"
          value={bgrToHex(highlight)}
          onChange={(e) => useEditor.getState().setHighlight(hexToBgr(e.target.value))}
        />
        <button
          type="button"
          className="apply-btn"
          disabled={!hasSelection}
          title="Apply highlight to selection"
          aria-label="Apply highlight to selection"
          onClick={() => useEditor.getState().applyHighlightToSelection()}
        >
          <PaintbrushIcon />
        </button>
      </label>

      <label className="color-control">
        Text
        <input
          ref={textColourInputRef}
          type="color"
          value={bgrToHex(textColour)}
          onChange={(e) => useEditor.getState().setTextColour(hexToBgr(e.target.value))}
        />
        <button
          type="button"
          className="apply-btn"
          disabled={!hasTextColourTarget}
          title="Apply text colour to selection"
          aria-label="Apply text colour to selection"
          onClick={() => useEditor.getState().applyTextColourToSelection()}
        >
          <PaintbrushIcon />
        </button>
      </label>

      <label className="toggle-control">
        <input
          type="checkbox"
          checked={zoomToGrid}
          onChange={(e) => useEditor.getState().setZoomToGrid(e.target.checked)}
        />
        Zoom to grid
      </label>

      <span className="filename">
        {fileName ?? "No file"}
        {dirty ? " •" : ""}
      </span>

      <input
        ref={fileInputRef}
        type="file"
        accept=".cwd,application/json,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.pdf,image/*,application/pdf"
        className="hidden-file-input"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void openFile(file);
          e.target.value = "";
        }}
      />
    </header>
  );
}
