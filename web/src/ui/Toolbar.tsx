/** The tool palette: selects the active pointer tool (see web/editor.md). The
 * `select` tool is the default (cell entry & selection); the rest create or
 * erase annotations. Rendered inline in the top toolbar. A text-size slider
 * also appears whenever it's relevant: while the `text` tool is active (sizing
 * the annotation about to be created) or a text annotation is selected (sizing
 * it directly, showing that annotation's own size). */

import { useEffect, useRef, useState, type ComponentType, type SVGProps } from "react";
import { useEditor, type Tool } from "../state/store.ts";
import { defaultTextAnnotationSize } from "../annotations/sizes.ts";
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

/** Slider bounds (source-image pixels) for the text-annotation size control. */
const TEXT_SIZE_MIN = 4;
const TEXT_SIZE_MAX = 400;

export function Toolbar() {
  const tool = useEditor((s) => s.tool);
  const setTool = useEditor((s) => s.setTool);
  const hasDoc = useEditor((s) => s.doc !== null);
  const hasSelectedTextAnnotation = useEditor((s) => {
    if (s.selectedAnnotationId === null) return false;
    const a = s.doc?.annotations.find((x) => x.id === s.selectedAnnotationId);
    return a != null && a.type === "text";
  });
  const showTextSize = tool === "text" || hasSelectedTextAnnotation;

  // The size the slider should show: the selected text annotation's own size
  // (falling back to the document default for one predating the field), or
  // the "pen" size that'll be used for an annotation about to be created.
  const targetSize = useEditor((s) => {
    if (s.selectedAnnotationId !== null) {
      const a = s.doc?.annotations.find((x) => x.id === s.selectedAnnotationId);
      if (a && a.type === "text") return a.fontSize ?? (s.doc ? defaultTextAnnotationSize(s.doc) : s.textSize);
    }
    return s.textSize;
  });

  // Local state drives the slider directly so dragging is visually smooth;
  // it's resynced whenever the underlying target (selection or pen) changes.
  const [sliderValue, setSliderValue] = useState(targetSize);
  useEffect(() => setSliderValue(targetSize), [targetSize]);

  // As with the colour inputs, commit to the store only on the native
  // "change" (drag release), not every "input" tick, so resizing is a single
  // undo step. The slider is conditionally mounted, so the listener has to be
  // re-attached whenever it (re)appears — hence the showTextSize dependency.
  const textSizeRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const el = textSizeRef.current;
    if (!el) return;
    const onCommit = (e: Event) => {
      const s = useEditor.getState();
      s.setTextSize(Number((e.target as HTMLInputElement).value));
      s.applyTextSizeToSelection(); // no-op unless a text annotation is selected
    };
    el.addEventListener("change", onCommit);
    return () => el.removeEventListener("change", onCommit);
  }, [showTextSize]);

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
      {showTextSize && (
        <label className="text-size-control" title="Text annotation size">
          <input
            ref={textSizeRef}
            type="range"
            min={TEXT_SIZE_MIN}
            max={TEXT_SIZE_MAX}
            step={1}
            disabled={!hasDoc}
            value={sliderValue}
            aria-label="Text size"
            onChange={(e) => setSliderValue(Number(e.target.value))}
          />
          <span className="text-size-value">{Math.round(sliderValue)}</span>
        </label>
      )}
    </div>
  );
}
