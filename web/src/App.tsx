import { useCallback, useState } from "react";
import { useEditor } from "./state/store.ts";
import { openCwdFile } from "./lib/files.ts";
import { MenuBar } from "./ui/MenuBar.tsx";
import { Toolbar } from "./ui/Toolbar.tsx";
import { CanvasEditor } from "./canvas/CanvasEditor.tsx";

export function App() {
  const doc = useEditor((s) => s.doc);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const loadFile = useCallback(async (file: File) => {
    try {
      const loaded = await openCwdFile(file);
      useEditor
        .getState()
        .loadDocument(
          loaded.doc,
          { element: loaded.image, width: loaded.width, height: loaded.height },
          loaded.fileName,
        );
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) void loadFile(file);
    },
    [loadFile],
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
          <>
            <CanvasEditor />
            <Toolbar />
          </>
        ) : (
          <div className="empty-state">
            <h1>Gridfill Editor</h1>
            <p>Open a .cwd document to start filling in the grid.</p>
            <p className="hint">Use File → Open, or drag a .cwd file here.</p>
          </div>
        )}
        {dragging && <div className="drop-overlay">Drop a .cwd file to open</div>}
      </main>
      {error && (
        <div className="error-toast" onClick={() => setError(null)}>
          {error}
        </div>
      )}
    </div>
  );
}
