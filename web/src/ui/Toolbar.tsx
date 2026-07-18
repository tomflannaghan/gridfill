/** The tool palette: selects the active pointer tool (see web/editor.md). The
 * `select` tool is the default (cell entry & selection); the rest create or
 * erase annotations. */

import type { ReactNode } from "react";
import { useEditor, type Tool } from "../state/store.ts";

interface ToolDef {
  tool: Tool;
  label: string;
  hint: string;
  icon: ReactNode;
}

const S = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

const TOOLS: ToolDef[] = [
  {
    tool: "select",
    label: "Select",
    hint: "Select — fill cells, move & edit annotations",
    icon: (
      <svg {...S}>
        <path d="M5 3l6 16 2-6 6-2z" />
      </svg>
    ),
  },
  {
    tool: "text",
    label: "Text",
    hint: "Text — click to add a text annotation",
    icon: (
      <svg {...S}>
        <path d="M5 5h14M12 5v14" />
      </svg>
    ),
  },
  {
    tool: "line",
    label: "Line",
    hint: "Line — drag to draw a straight line",
    icon: (
      <svg {...S}>
        <path d="M5 19L19 5" />
      </svg>
    ),
  },
  {
    tool: "curve",
    label: "Curve",
    hint: "Curve — click points; double-click or Enter to finish",
    icon: (
      <svg {...S}>
        <path d="M4 17c4 0 4-10 8-10s4 10 8 10" />
      </svg>
    ),
  },
  {
    tool: "eraser",
    label: "Eraser",
    hint: "Eraser — click an annotation to delete it",
    icon: (
      <svg {...S}>
        <path d="M4 15l7-7 6 6-4 4H8zM14 19h6" />
      </svg>
    ),
  },
];

export function Toolbar() {
  const tool = useEditor((s) => s.tool);
  const setTool = useEditor((s) => s.setTool);

  return (
    <div className="toolbar" role="toolbar" aria-label="Annotation tools">
      {TOOLS.map((t) => (
        <button
          key={t.tool}
          type="button"
          className={tool === t.tool ? "tool active" : "tool"}
          title={t.hint}
          aria-label={t.label}
          aria-pressed={tool === t.tool}
          onClick={() => setTool(t.tool)}
        >
          {t.icon}
        </button>
      ))}
    </div>
  );
}
