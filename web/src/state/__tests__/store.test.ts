import { describe, it, expect, beforeEach } from "vitest";
import { useEditor } from "../store.ts";
import type { Cwd } from "../../model/cwd.ts";
import { createLine, createText } from "../../annotations/types.ts";

function emptyDoc(): Cwd {
  return { format: "gridfill", version: 1, image: { encoding: "png", data: "" }, grids: [], annotations: [] };
}

function loadEmpty(): void {
  useEditor
    .getState()
    .loadDocument(emptyDoc(), { element: {} as HTMLImageElement, width: 100, height: 100 }, "t.cwd");
}

describe("annotation CRUD", () => {
  beforeEach(loadEmpty);

  it("adds, updates and deletes by id", () => {
    const s = useEditor.getState();
    const text = createText(0.1, 0.2, "hi", null);
    s.addAnnotation(text);
    expect(useEditor.getState().doc!.annotations).toHaveLength(1);

    s.updateAnnotation(text.id, { ...text, text: "bye" });
    expect((useEditor.getState().doc!.annotations[0] as typeof text).text).toBe("bye");

    s.deleteAnnotation(text.id);
    expect(useEditor.getState().doc!.annotations).toHaveLength(0);
  });

  it("clears the annotation selection when its annotation is deleted", () => {
    const s = useEditor.getState();
    const line = createLine([0, 0], [1, 1], null);
    s.addAnnotation(line);
    s.selectAnnotation(line.id);
    expect(useEditor.getState().selectedAnnotationId).toBe(line.id);
    s.deleteAnnotation(line.id);
    expect(useEditor.getState().selectedAnnotationId).toBeNull();
  });
});

describe("undo / redo", () => {
  beforeEach(loadEmpty);

  it("undoes and redoes an annotation add", () => {
    const s = useEditor.getState();
    s.addAnnotation(createText(0.1, 0.2, "hi", null));
    expect(useEditor.getState().doc!.annotations).toHaveLength(1);

    s.undo();
    expect(useEditor.getState().doc!.annotations).toHaveLength(0);

    s.redo();
    expect(useEditor.getState().doc!.annotations).toHaveLength(1);
  });

  it("does nothing when there is no history", () => {
    const s = useEditor.getState();
    s.undo();
    expect(useEditor.getState().doc!.annotations).toHaveLength(0);
  });

  it("drops the redo stack after a fresh change", () => {
    const s = useEditor.getState();
    s.addAnnotation(createText(0, 0, "a", null));
    s.undo();
    s.addAnnotation(createText(1, 1, "b", null));
    s.redo(); // nothing to redo — the branch was discarded
    const texts = useEditor.getState().doc!.annotations;
    expect(texts).toHaveLength(1);
    expect((texts[0] as { text: string }).text).toBe("b");
  });
});

describe("tools", () => {
  beforeEach(loadEmpty);

  it("switching tool clears the annotation selection", () => {
    const s = useEditor.getState();
    const line = createLine([0, 0], [1, 1], null);
    s.addAnnotation(line);
    s.selectAnnotation(line.id);
    s.setTool("line");
    expect(useEditor.getState().tool).toBe("line");
    expect(useEditor.getState().selectedAnnotationId).toBeNull();
  });
});
