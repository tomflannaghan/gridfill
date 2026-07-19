/** Top bar: an icon-only toolbar — file actions (Open / Save / Export), the
 * annotation tool palette, the text/highlight colour pills, and the "zoom to
 * grid" view toggle. */

import { useEffect, useRef } from "react";
import { useEditor } from "../state/store.ts";
import { saveCwd, exportImage } from "../lib/files.ts";
import { confirmDiscardIfDirty, useOpenFile } from "../lib/useOpenFile.ts";
import { bgrToHex, contrastFg, hexToBgr } from "../model/colour.ts";
import { IconFolderOpen, IconSave, IconDownload, IconPaintBucket, IconAspectRatio } from "./icons.tsx";
import { Toolbar } from "./Toolbar.tsx";
import logoUrl from "../assets/logo.svg";

interface Props {
  onError(message: string): void;
}

export function MenuBar({ onError }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { openFile, detecting } = useOpenFile(onError);
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
  const selectedAnnotationId = useEditor((s) => s.selectedAnnotationId);
  const hasSelection = selection !== null || selectedCells.length > 0;
  const hasTextTarget = hasSelection || selectedAnnotationId !== null;

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

  const hasDoc = doc !== null;

  return (
    <header className="menubar">
      <button
        type="button"
        className="icon-btn"
        disabled={!hasDoc}
        onClick={() => {
          if (!confirmDiscardIfDirty()) return;
          useEditor.getState().closeDocument();
        }}
        title="Close document and return to the start screen"
        aria-label="Gridfill"
      >
        <img src={logoUrl} alt="" className="brand-logo" />
      </button>

      <span className="menubar-divider" />

      <button
        type="button"
        className="icon-btn"
        disabled={detecting}
        onClick={() => {
          if (!confirmDiscardIfDirty()) return;
          fileInputRef.current?.click();
        }}
        title="Open a .cwd document, or an image/PDF to detect a grid from via the gridfill backend"
        aria-label={detecting ? "Loading…" : "Open"}
      >
        <IconFolderOpen />
      </button>
      <button
        type="button"
        className="icon-btn"
        disabled={!hasDoc}
        onClick={() => {
          if (doc) {
            saveCwd(doc, fileName);
            useEditor.getState().markSaved();
          }
        }}
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

      <div className="colour-pill">
        <button
          type="button"
          className="colour-pill-apply"
          disabled={!hasTextTarget}
          onClick={() => useEditor.getState().applyTextColourToSelection()}
          title="Apply text colour to the current selection"
          aria-label="Apply text colour"
        >
          <span className="colour-swatch-glyph" aria-hidden="true">
            T
          </span>
        </button>
        <button
          type="button"
          className="colour-pill-swatch"
          style={{ background: bgrToHex(textColour), color: contrastFg(textColour) }}
          title="Choose text colour"
          aria-label="Choose text colour"
          onClick={() => textColourInputRef.current?.click()}
        />
      </div>
      <input
        ref={textColourInputRef}
        type="color"
        className="hidden-color-input"
        value={bgrToHex(textColour)}
        onChange={(e) => useEditor.getState().setTextColour(hexToBgr(e.target.value))}
      />

      <div className="colour-pill">
        <button
          type="button"
          className="colour-pill-apply"
          disabled={!hasSelection}
          onClick={() => useEditor.getState().applyOrClearHighlightToSelection()}
          title="Apply highlight to the current selection, or clear it if already applied"
          aria-label="Apply or clear highlight"
        >
          <IconPaintBucket />
        </button>
        <button
          type="button"
          className="colour-pill-swatch"
          style={{ background: bgrToHex(highlight), color: contrastFg(highlight) }}
          title="Choose highlight colour"
          aria-label="Choose highlight colour"
          onClick={() => highlightInputRef.current?.click()}
        />
      </div>
      <input
        ref={highlightInputRef}
        type="color"
        className="hidden-color-input"
        value={bgrToHex(highlight)}
        onChange={(e) => useEditor.getState().setHighlight(hexToBgr(e.target.value))}
      />

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
