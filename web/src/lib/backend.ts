/** Talks to the gridfill HTTP backend (python/src/gridfill/server.py): upload
 * a scanned image or PDF, get back a detected, blank `.cwd` document.
 *
 * The backend is optional — the editor works standalone on `.cwd` files
 * (lib/files.ts) — this is only needed to go from a raw scan to one.
 */

import { loadCwdText, stripExtension, type LoadedDocument } from "./files.ts";

/** Overridable via `VITE_GRIDFILL_API_URL`; matches `gridfill-server`'s default. */
const API_BASE_URL =
  (import.meta.env.VITE_GRIDFILL_API_URL as string | undefined) ?? "http://127.0.0.1:8420";

/** Upload an image or PDF to the backend and load the `.cwd` document it detects. */
export async function detectFromImage(file: File): Promise<LoadedDocument> {
  const body = new FormData();
  body.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/detect`, { method: "POST", body });
  } catch {
    throw new Error(
      `Could not reach the gridfill backend at ${API_BASE_URL}. Is it running ` +
        "(gridfill-server)?",
    );
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const message =
      typeof detail?.detail === "string" ? detail.detail : `Detection failed (${response.status})`;
    throw new Error(message);
  }

  return loadCwdText(await response.text(), stripExtension(file.name) + ".cwd");
}
