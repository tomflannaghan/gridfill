/** Top bar: File actions (Open / Save / Export) and the highlight colour. */

import { useRef } from "react";
import { useEditor } from "../state/store.ts";
import { openCwdFile, saveCwd, exportImage } from "../lib/files.ts";
import { bgrToHex, hexToBgr } from "../model/color.ts";

interface Props {
  onError(message: string): void;
}

export function MenuBar({ onError }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const doc = useEditor((s) => s.doc);
  const fileName = useEditor((s) => s.fileName);
  const highlight = useEditor((s) => s.highlight);
  const textColor = useEditor((s) => s.textColor);
  const dirty = useEditor((s) => s.dirty);

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
      <span className="brand">Gridfill Editor</span>

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
          if (s.doc && s.image) exportImage(s.doc, s.image.element, "png", s.fileName);
        }}
      >
        Export PNG
      </button>
      <button
        type="button"
        disabled={!hasDoc}
        onClick={() => {
          const s = useEditor.getState();
          if (s.doc && s.image) exportImage(s.doc, s.image.element, "jpeg", s.fileName);
        }}
      >
        Export JPEG
      </button>

      <label className="color-control">
        Highlight
        <input
          type="color"
          value={bgrToHex(highlight)}
          onChange={(e) => useEditor.getState().setHighlight(hexToBgr(e.target.value))}
        />
      </label>

      <label className="color-control">
        Text
        <input
          type="color"
          value={bgrToHex(textColor)}
          onChange={(e) => useEditor.getState().setTextColor(hexToBgr(e.target.value))}
        />
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
