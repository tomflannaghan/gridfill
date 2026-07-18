import { describe, it, expect, vi } from "vitest";
import { StrictMode } from "react";
import { render, screen, fireEvent, act, cleanup } from "@testing-library/react";
import { AnnotationEditor, type AnnotationEdit } from "../AnnotationEditor.tsx";

const EDIT: AnnotationEdit = { x: 10, y: 20, value: "", fontSize: 14, color: "#000000" };

/** Resolve after one animation frame, so the editor's deferred focus/blur-arm
 * effect has run. */
const nextFrame = () =>
  act(() => new Promise<void>((resolve) => requestAnimationFrame(() => resolve())));

function renderEditor(onCommit = vi.fn(), wrap = false) {
  const ui = (
    <AnnotationEditor edit={EDIT} onChange={() => {}} onCommit={onCommit} onCancel={() => {}} />
  );
  render(wrap ? <StrictMode>{ui}</StrictMode> : ui);
  return onCommit;
}

describe("AnnotationEditor", () => {
  // Regression test for the StrictMode mount bug: focusing synchronously on
  // mount let the remount's blur commit an empty edit and close the box before
  // any typing. The fix defers focus and only arms blur after a frame.
  it("does not commit on a blur before the first frame", () => {
    const onCommit = renderEditor();
    fireEvent.blur(screen.getByRole("textbox"));
    expect(onCommit).not.toHaveBeenCalled();
  });

  it("commits on a blur once settled (a real click-away)", async () => {
    const onCommit = renderEditor();
    await nextFrame();
    fireEvent.blur(screen.getByRole("textbox"));
    expect(onCommit).toHaveBeenCalledTimes(1);
  });

  it("survives a StrictMode mount without committing", async () => {
    // The double-invoked mount must not fire a spurious commit.
    const onCommit = renderEditor(vi.fn(), true);
    await nextFrame();
    expect(onCommit).not.toHaveBeenCalled();
    // And the input is focused and ready after the frame.
    expect(document.activeElement).toBe(screen.getByRole("textbox"));
    cleanup();
  });

  it("commits on Enter and cancels on Escape regardless of the blur arming", () => {
    const onCommit = vi.fn();
    const onCancel = vi.fn();
    render(
      <AnnotationEditor edit={EDIT} onChange={() => {}} onCommit={onCommit} onCancel={onCancel} />,
    );
    const input = screen.getByRole("textbox");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onCommit).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(input, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
