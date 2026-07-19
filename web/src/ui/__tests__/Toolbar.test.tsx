import { describe, it, expect, beforeEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";
import { Toolbar } from "../Toolbar.tsx";
import { useEditor } from "../../state/store.ts";
import type { Cwd } from "../../model/cwd.ts";
import { createLine, createText, type TextAnnotation } from "../../annotations/types.ts";

function emptyDoc(): Cwd {
  return { format: "gridfill", version: 2, image: { encoding: "png", data: "" }, grids: [], annotations: [] };
}

function loadEmpty(): void {
  useEditor
    .getState()
    .loadDocument(emptyDoc(), { element: {} as HTMLImageElement, width: 100, height: 100 }, "t.cwd");
}

describe("Toolbar text-size slider", () => {
  beforeEach(() => {
    loadEmpty();
    useEditor.getState().setTool("select"); // tool isn't reset by loadDocument
    cleanup();
  });

  it("is hidden for the select tool with nothing selected", () => {
    const { queryByLabelText } = render(<Toolbar />);
    expect(queryByLabelText("Text size")).toBeNull();
  });

  it("appears while the text tool is active", () => {
    useEditor.getState().setTool("text");
    const { queryByLabelText } = render(<Toolbar />);
    expect(queryByLabelText("Text size")).not.toBeNull();
  });

  it("appears when a text annotation is selected, even with the select tool", () => {
    const s = useEditor.getState();
    const text = createText(0, 0, "hi", null);
    s.addAnnotation(text);
    s.selectAnnotation(text.id);

    const { queryByLabelText } = render(<Toolbar />);
    expect(queryByLabelText("Text size")).not.toBeNull();
  });

  it("stays hidden when a non-text annotation is selected", () => {
    const s = useEditor.getState();
    const line = createLine([0, 0], [10, 10], null);
    s.addAnnotation(line);
    s.selectAnnotation(line.id);

    const { queryByLabelText } = render(<Toolbar />);
    expect(queryByLabelText("Text size")).toBeNull();
  });

  it("shows the selected text annotation's own size, not the pen default", () => {
    const s = useEditor.getState();
    s.setTextSize(50);
    const text = createText(0, 0, "hi", null, 12);
    s.addAnnotation(text);
    s.selectAnnotation(text.id);

    const { getByLabelText } = render(<Toolbar />);
    expect((getByLabelText("Text size") as HTMLInputElement).value).toBe("12");
  });

  it("resizes the selected text annotation when the slider is released", () => {
    const s = useEditor.getState();
    const text = createText(0, 0, "hi", null, 12);
    s.addAnnotation(text);
    s.selectAnnotation(text.id);
    const undoDepth = useEditor.getState().past.length;

    const { getByLabelText } = render(<Toolbar />);
    fireEvent.change(getByLabelText("Text size"), { target: { value: "30" } });

    const updated = useEditor.getState().doc!.annotations[0] as TextAnnotation;
    expect(updated.fontSize).toBe(30);
    expect(useEditor.getState().past.length).toBe(undoDepth + 1); // single step
    expect(useEditor.getState().textSize).toBe(30); // becomes the new pen default too
  });
});
