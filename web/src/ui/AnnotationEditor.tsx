/** An inline text input floating over the canvas for editing an annotation. */

import { useEffect, useRef } from "react";

export interface AnnotationEdit {
  /** Canvas-space position (CSS px) of the annotation's top-left. */
  x: number;
  y: number;
  value: string;
  fontSize: number;
  /** CSS colour the text is drawn in, matching how it renders on the canvas. */
  colour: string;
}

interface Props {
  edit: AnnotationEdit;
  onChange(value: string): void;
  onCommit(): void;
  onCancel(): void;
}

export function AnnotationEditor({ edit, onChange, onCommit, onCancel }: Props) {
  const ref = useRef<HTMLInputElement>(null);
  // Focus (and enable blur-to-commit) on the next frame rather than synchronously
  // on mount. React StrictMode (dev) mounts, unmounts and remounts the input in
  // one tick; focusing synchronously loses the focus to that churn and blurs the
  // field, committing an empty edit before any typing. Deferring a frame lets the
  // churn settle so we focus the live node and only then honour blur.
  const acceptBlur = useRef(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      ref.current?.focus();
      ref.current?.select();
      acceptBlur.current = true;
    });
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <input
      ref={ref}
      className="annotation-input"
      style={{
        left: edit.x,
        top: edit.y,
        fontSize: edit.fontSize,
        color: edit.colour,
      }}
      value={edit.value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={() => {
        if (acceptBlur.current) onCommit();
      }}
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.key === "Enter") onCommit();
        else if (e.key === "Escape") onCancel();
      }}
    />
  );
}
