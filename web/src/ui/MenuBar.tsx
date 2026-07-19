/** Top bar: an icon-only toolbar — file actions (Open / Save / Export), the
 * annotation tool palette, the text/highlight colour swatches with a clear-
 * highlight button, and the "zoom to grid" view toggle. */

import { useEffect, useRef, useState } from "react";
import { useEditor } from "../state/store.ts";
import { openCwdFile, saveCwd, exportImage } from "../lib/files.ts";
import { detectFromImage } from "../lib/backend.ts";
import { bgrToHex, contrastFg, hexToBgr } from "../model/colour.ts";
import {
  IconFolderOpen,
  IconSave,
  IconDownload,
  IconPaintBucket,
  IconSlashCircle,
  IconAspectRatio,
} from "./icons.tsx";
import { Toolbar } from "./Toolbar.tsx";
import logoUrl from "../assets/logo.svg";

interface Props {
  onError(message: string): void;
}

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
  const dirty = useEditor((s) => s.dirty);
  const selection = useEditor((s) => s.selection);
  const selectedCells = useEditor((s) => s.selectedCells);
  const hasSelection = selection !== null || selectedCells.length > 0;

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
        className="icon-btn"
        disabled={detecting}
        onClick={() => fileInputRef.current?.click()}
        title="Open a .cwd document, or an image/PDF to detect a grid from via the gridfill backend"
        aria-label={detecting ? "Loading…" : "Open"}
      >
        <IconFolderOpen />
      </button>
      <button
        type="button"
        className="icon-btn"
        disabled={!hasDoc}
        onClick={() => doc && saveCwd(doc, fileName)}
        title="Save"
        aria-label="Save"
      >
        <IconSave />
      </button>
      <button
        type="button"
        className="icon-btn"
        disabled={!hasDoc}
        onClick={() => {
          const s = useEditor.getState();
          if (s.doc && s.image) exportImage(s.doc, s.image.element, s.fileName);
        }}
        title="Export image"
        aria-label="Export image"
      >
        <IconDownload />
      </button>

      <span className="menubar-divider" />

      <Toolbar />

      <span className="menubar-divider" />

      <button
        type="button"
        className="colour-swatch"
        style={{ background: bgrToHex(textColour), color: contrastFg(textColour) }}
        title="Text colour — applies to the current selection"
        aria-label="Text colour"
        onClick={() => textColourInputRef.current?.click()}
      >
        <span className="colour-swatch-glyph" aria-hidden="true">
          T
        </span>
      </button>
      <input
        ref={textColourInputRef}
        type="color"
        className="hidden-color-input"
        value={bgrToHex(textColour)}
        onChange={(e) => useEditor.getState().setTextColour(hexToBgr(e.target.value))}
      />

      <button
        type="button"
        className="colour-swatch"
        style={{ background: bgrToHex(highlight), color: contrastFg(highlight) }}
        title="Highlight (cell background) colour — applies to the current selection"
        aria-label="Highlight colour"
        onClick={() => highlightInputRef.current?.click()}
      >
        <IconPaintBucket />
      </button>
      <input
        ref={highlightInputRef}
        type="color"
        className="hidden-color-input"
        value={bgrToHex(highlight)}
        onChange={(e) => useEditor.getState().setHighlight(hexToBgr(e.target.value))}
      />

      <button
        type="button"
        className="icon-btn"
        disabled={!hasSelection}
        onClick={() => useEditor.getState().clearHighlightFromSelection()}
        title="Clear highlight — removes the background of the current selection"
        aria-label="Clear highlight"
      >
        <IconSlashCircle />
      </button>

      <span className="menubar-divider" />

      <button
        type="button"
        className={zoomToGrid ? "icon-btn active" : "icon-btn"}
        onClick={() => useEditor.getState().setZoomToGrid(!zoomToGrid)}
        title="Zoom to grid — fit the view to the selected grid"
        aria-label="Zoom to grid"
        aria-pressed={zoomToGrid}
      >
        <IconAspectRatio />
      </button>

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
