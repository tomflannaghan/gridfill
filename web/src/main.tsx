import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
import { useEditor } from "./state/store.ts";
import "./index.css";

// Expose the store during development so it can be inspected / driven in tests.
if (import.meta.env.DEV) {
  (window as unknown as { __editor: typeof useEditor }).__editor = useEditor;
}

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
