/** The tool palette: selects the active pointer tool (see web/editor.md). The
 * `select` tool is the default (cell entry & selection); the rest create or
 * erase annotations. Rendered inline in the top toolbar. A size slider also
 * appears whenever it's relevant, sizing whichever dimension the context calls
 * for: the font size of text annotations (the `text` tool, or a selected text
 * annotation), or the stroke width of strokes (the `line`/`curve` tools, or a
 * selected line/curve). It shows the selected annotation's own value when one
 * is selected, otherwise the "pen" value new annotations will be created at. */

import { useEffect, useRef, useState, type ComponentType, type SVGProps } from "react";
import { useEditor, selectedAnnotation, type EditorState, type Tool } from "../state/store.ts";
import { defaultLineWidth, defaultTextAnnotationSize } from "../annotations/sizes.ts";
import { isStroked } from "../annotations/types.ts";
import { IconCursor, IconCursorText, IconSlashLg, IconBezier2, IconEraser } from "./icons.tsx";

interface ToolDef {
  tool: Tool;
  label: string;
  hint: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
}

const TOOLS: ToolDef[] = [
  { tool: "select", label: "Select", hint: "Select — fill cells, move & edit annotations", Icon: IconCursor },
  { tool: "text", label: "Text", hint: "Text — click to add a text annotation", Icon: IconCursorText },
  { tool: "line", label: "Line", hint: "Line — drag to draw a straight line", Icon: IconSlashLg },
  { tool: "curve", label: "Curve", hint: "Curve — click points; double-click or Enter to finish", Icon: IconBezier2 },
  { tool: "eraser", label: "Eraser", hint: "Eraser — click an annotation to delete it", Icon: IconEraser },
];

/** Which dimension the size slider currently edits. */
type SizeControl = "text" | "line";

/** Slider presentation and bounds (source-image pixels) per control. */
const SIZE_CONTROLS: Record<SizeControl, { label: string; title: string; min: number; max: number }> = {
  text: { label: "Text size", title: "Text annotation size", min: 4, max: 400 },
  line: { label: "Line width", title: "Annotation line width", min: 1, max: 100 },
};

/** The control a tool implies while nothing is selected. */
const TOOL_CONTROLS: Partial<Record<Tool, SizeControl>> = {
  text: "text",
  line: "line",
  curve: "line",
};

/** The control to show: the selected annotation's own dimension takes priority
 * over the active tool's; null hides the slider entirely. */
function activeControl(s: EditorState): SizeControl | null {
  const a = selectedAnnotation(s);
  if (a) return a.type === "text" ? "text" : "line";
  return TOOL_CONTROLS[s.tool] ?? null;
}

/** The value the slider should show: the selected annotation's own size
 * (falling back to the default for one predating the field), or the "pen" size
 * that'll be used for an annotation about to be created. */
function activeValue(s: EditorState): number {
  const a = selectedAnnotation(s);
  if (a?.type === "text") {
    return a.fontSize ?? (s.doc ? defaultTextAnnotationSize(s.doc) : s.textSize);
  }
  if (a && isStroked(a)) {
    return a.lineWidth ?? (s.image ? defaultLineWidth(s.image.height) : s.lineWidth);
  }
  return activeControl(s) === "line" ? s.lineWidth : s.textSize;
}

export function Toolbar() {
  const tool = useEditor((s) => s.tool);
  const setTool = useEditor((s) => s.setTool);
  const hasDoc = useEditor((s) => s.doc !== null);
  const control = useEditor(activeControl);
  const targetValue = useEditor(activeValue);

  // Local state drives the slider directly so dragging is visually smooth;
  // it's resynced whenever the underlying target (selection or pen) changes.
  const [sliderValue, setSliderValue] = useState(targetValue);
  useEffect(() => setSliderValue(targetValue), [targetValue]);

  // As with the colour inputs, commit to the store only on the native
  // "change" (drag release), not every "input" tick, so resizing is a single
  // undo step. The slider is conditionally mounted (and switches meaning), so
  // the listener has to be re-attached whenever it does — hence the dependency.
  const sliderRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const el = sliderRef.current;
    if (!el) return;
    const onCommit = (e: Event) => {
      const s = useEditor.getState();
      const value = Number((e.target as HTMLInputElement).value);
      // The apply-to-selection calls are no-ops unless a matching annotation
      // is selected.
      if (control === "line") {
        s.setLineWidth(value);
        s.applyLineWidthToSelection();
      } else {
        s.setTextSize(value);
        s.applyTextSizeToSelection();
      }
    };
    el.addEventListener("change", onCommit);
    return () => el.removeEventListener("change", onCommit);
  }, [control]);

  const size = control ? SIZE_CONTROLS[control] : null;

  return (
    <div className="toolbar" role="toolbar" aria-label="Annotation tools">
      {TOOLS.map(({ tool: t, label, hint, Icon }) => (
        <button
          key={t}
          type="button"
          className={tool === t ? "icon-btn active" : "icon-btn"}
          disabled={!hasDoc}
          title={hint}
          aria-label={label}
          aria-pressed={tool === t}
          onClick={() => setTool(t)}
        >
          <Icon />
        </button>
      ))}
      {size && (
        <label className="size-control" title={size.title}>
          <input
            ref={sliderRef}
            type="range"
            min={size.min}
            max={size.max}
            step={1}
            disabled={!hasDoc}
            value={sliderValue}
            aria-label={size.label}
            onChange={(e) => setSliderValue(Number(e.target.value))}
          />
          <span className="size-value">{Math.round(sliderValue)}</span>
        </label>
      )}
    </div>
  );
}
