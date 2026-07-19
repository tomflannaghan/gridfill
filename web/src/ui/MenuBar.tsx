/** Top bar: File actions (Open / Save / Export) and the highlight colour. */

import { useRef } from "react";
import { useEditor } from "../state/store.ts";
import { openCwdFile, saveCwd, exportImage } from "../lib/files.ts";
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
  const doc = useEditor((s) => s.doc);
  const fileName = useEditor((s) => s.fileName);
  const highlight = useEditor((s) => s.highlight);
  const textColour = useEditor((s) => s.textColour);
  const zoomToGrid = useEditor((s) => s.zoomToGrid);
  const selection = useEditor((s) => s.selection);
  const selectedCells = useEditor((s) => s.selectedCells);
  const dirty = useEditor((s) => s.dirty);

  const hasSelection = selection !== null || selectedCells.length > 0;

  const openFile = async (file: File) => {
    try {
      const loaded = await openCwdFile(file);
      useEditor
        .getState()
        .loadDocument(
          loaded.doc,
          { element: loaded.image, width: loaded.width, height: loaded.height },
          loaded.fileName,
        );
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    }
  };

  const hasDoc = doc !== null;

  return (
    <header className="menubar">
      <span className="brand">
        <img src={logoUrl} alt="" className="brand-logo" />
        Gridfill Editor
      </span>

      <button type="button" onClick={() => fileInputRef.current?.click()}>
        Open…
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
        Export
      </button>

      <label className="color-control">
        Highlight
        <input
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
          type="color"
          value={bgrToHex(textColour)}
          onChange={(e) => useEditor.getState().setTextColour(hexToBgr(e.target.value))}
        />
        <button
          type="button"
          className="apply-btn"
          disabled={!hasSelection}
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
        accept=".cwd,application/json"
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
