/** Shared "open a file" logic for the MenuBar's Open button and drag-and-drop:
 * a `.cwd` is parsed directly, anything else is sent to the backend for grid
 * detection. Keeping this in one place means both entry points accept the
 * same file types and behave identically. */

import { useState } from "react";
import { useEditor } from "../state/store.ts";
import { openCwdFile } from "./files.ts";
import { detectFromImage } from "./backend.ts";

export function isCwdFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".cwd") || file.type === "application/json";
}

/** True if there's no unsaved document, or the user confirms discarding it. */
export function confirmDiscardIfDirty(): boolean {
  return !useEditor.getState().dirty || window.confirm("You have unsaved changes. Discard them?");
}

export function useOpenFile(onError: (message: string) => void) {
  const [detecting, setDetecting] = useState(false);

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

  return { openFile, detecting };
}
