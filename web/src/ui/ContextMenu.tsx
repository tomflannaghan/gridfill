/** A tiny right-click menu (currently just Delete for annotations). */

import { useEffect } from "react";

export interface ContextMenuState {
  x: number;
  y: number;
  onDelete(): void;
}

interface Props {
  menu: ContextMenuState;
  onClose(): void;
}

export function ContextMenu({ menu, onClose }: Props) {
  useEffect(() => {
    const close = () => onClose();
    window.addEventListener("pointerdown", close);
    window.addEventListener("blur", close);
    return () => {
      window.removeEventListener("pointerdown", close);
      window.removeEventListener("blur", close);
    };
  }, [onClose]);

  return (
    <div className="context-menu" style={{ left: menu.x, top: menu.y }}>
      <button
        type="button"
        onClick={() => {
          menu.onDelete();
          onClose();
        }}
      >
        Delete annotation
      </button>
    </div>
  );
}
