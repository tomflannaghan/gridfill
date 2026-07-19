/** The tool palette: selects the active pointer tool (see web/editor.md). The
 * `select` tool is the default (cell entry & selection); the rest create or
 * erase annotations. Rendered inline in the top toolbar. */

import type { ComponentType, SVGProps } from "react";
import { useEditor, type Tool } from "../state/store.ts";
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

export function Toolbar() {
  const tool = useEditor((s) => s.tool);
  const setTool = useEditor((s) => s.setTool);
  const hasDoc = useEditor((s) => s.doc !== null);

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
    </div>
  );
}
