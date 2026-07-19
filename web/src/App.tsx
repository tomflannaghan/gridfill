import { useCallback, useEffect, useState } from "react";
import { useEditor } from "./state/store.ts";
import { decodeDocumentImage } from "./lib/files.ts";
import { confirmDiscardIfDirty, useOpenFile } from "./lib/useOpenFile.ts";
import { loadAutosave, saveAutosave, clearAutosave } from "./lib/autosave.ts";
import { MenuBar } from "./ui/MenuBar.tsx";
import { CanvasEditor } from "./canvas/CanvasEditor.tsx";
import { IconFolderOpen, IconSave, IconDownload } from "./ui/icons.tsx";
import logoUrl from "./assets/logo.svg";

/** Idle time after the last edit before it's written to auto-save storage. */
const AUTOSAVE_DEBOUNCE_MS = 800;

export function App() {
  const doc = useEditor((s) => s.doc);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  // Resume the last document on startup, if the browser auto-saved one and
  // nothing else got loaded in the meantime (e.g. a drag-drop that beat this
  // async restore).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const record = await loadAutosave();
      if (cancelled || !record || useEditor.getState().doc !== null) return;
      try {
        const { image, width, height } = await decodeDocumentImage(record.doc);
        if (cancelled || useEditor.getState().doc !== null) return;
        useEditor
          .getState()
          .loadDocument(record.doc, { element: image, width, height }, record.fileName);
      } catch {
        // Corrupt auto-save; start blank rather than fail to load.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Keep auto-save in step with the document: debounced while editing (so
  // fast typing doesn't write on every keystroke), flushed immediately when
  // the tab is hidden (closed, backgrounded) since a pending debounce may
  // never otherwise get to fire; cleared once the document is closed.
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let flush: (() => void) | null = null;

    const cancel = () => {
      if (timer !== null) clearTimeout(timer);
      timer = null;
      flush = null;
    };

    const onVisibilityChange = () => {
      if (document.hidden) flush?.();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    const unsubscribe = useEditor.subscribe((state, prev) => {
      if (state.doc === prev.doc && state.fileName === prev.fileName) return;
      cancel();
      if (state.doc === null) {
        void clearAutosave();
        return;
      }
      const { doc: nextDoc, fileName } = state;
      flush = () => {
        cancel();
        void saveAutosave(nextDoc, fileName);
      };
      timer = setTimeout(flush, AUTOSAVE_DEBOUNCE_MS);
    });

    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      cancel();
      unsubscribe();
    };
  }, []);

  const { openFile } = useOpenFile(setError);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file && confirmDiscardIfDirty()) void openFile(file);
    },
    [openFile],
  );

  return (
    <div
      className="app"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <MenuBar onError={setError} />
      <main className="stage">
        {doc ? (
          <CanvasEditor />
        ) : (
          <div className="empty-state">
            <img src={logoUrl} alt="" className="empty-logo" />
            <h1>Gridfill Editor</h1>
            <ol className="empty-steps">
              <li>
                Open a <strong>.pdf or image</strong> of a crossword grid — with{" "}
                <span className="inline-icon" title="Open" aria-label="Open">
                  <IconFolderOpen />
                </span>
                , or by dragging the file here. Gridfill will detect the grid layout automatically.
              </li>
              <li>Click a cell and type to fill in your solution.</li>
              <li>
                Save your progress any time with{" "}
                <span className="inline-icon" title="Save" aria-label="Save">
                  <IconSave />
                </span>
                . This writes a <strong>.cwd</strong> file, which you can reopen with{" "}
                <span className="inline-icon" title="Open" aria-label="Open">
                  <IconFolderOpen />
                </span>.
              </li>
              <li>
                When you're done, use{" "}
                <span className="inline-icon" title="Export image" aria-label="Export image">
                  <IconDownload />
                </span>{" "}
                to export an image of the filled grid.
              </li>
            </ol>
          </div>
        )}
        {dragging && <div className="drop-overlay">Drop a .cwd/.pdf file to open</div>}
      </main>
      {error && (
        <div className="error-toast" onClick={() => setError(null)}>
          {error}
        </div>
      )}
    </div>
  );
}
