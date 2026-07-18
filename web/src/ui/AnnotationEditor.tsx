/** An inline text input floating over the canvas for editing an annotation. */

import { useEffect, useRef } from "react";

export interface AnnotationEdit {
  index: number;
  /** Canvas-space position (CSS px) of the annotation's top-left. */
  x: number;
  y: number;
  value: string;
  fontSize: number;
  /** CSS colour the text is drawn in, matching how it renders on the canvas. */
  color: string;
}

interface Props {
  edit: AnnotationEdit;
  onChange(value: string): void;
  onCommit(): void;
  onCancel(): void;
}

export function AnnotationEditor({ edit, onChange, onCommit, onCancel }: Props) {
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    ref.current?.focus();
    ref.current?.select();
  }, []);

  return (
    <input
      ref={ref}
      className="annotation-input"
      style={{
        left: edit.x,
        top: edit.y,
        fontSize: edit.fontSize,
        color: edit.color,
      }}
      value={edit.value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onCommit}
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.key === "Enter") onCommit();
        else if (e.key === "Escape") onCancel();
      }}
    />
  );
}
