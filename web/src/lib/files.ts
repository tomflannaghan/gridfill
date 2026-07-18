/** Loading and saving files, entirely client-side (no backend).
 *
 * Open: read a `.cwd` file's text, parse it, and decode its embedded image.
 * Save: serialize the document and download it as a `.cwd`.
 * Export: render the filled grid (no editor chrome) to a PNG/JPEG download.
 */

import { parseCwd, serializeCwd, imageDataUri, type Cwd } from "../model/cwd.ts";
import { renderScene } from "../canvas/render.ts";
import { computeViewport } from "../canvas/viewport.ts";

export interface LoadedDocument {
  doc: Cwd;
  image: HTMLImageElement;
  width: number;
  height: number;
  fileName: string;
}

function decodeImage(dataUri: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Could not decode the document's embedded image"));
    img.src = dataUri;
  });
}

/** Parse a `.cwd` File and decode its image, ready to hand to the store. */
export async function openCwdFile(file: File): Promise<LoadedDocument> {
  const text = await file.text();
  const doc = parseCwd(text);
  const image = await decodeImage(imageDataUri(doc.image));
  return { doc, image, width: image.naturalWidth, height: image.naturalHeight, fileName: file.name };
}

function triggerDownload(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Serialize the document and download it as a `.cwd` (loss-free). */
export function saveCwd(doc: Cwd, fileName: string | null): void {
  const name = ensureExtension(fileName ?? "crossword.cwd", ".cwd");
  triggerDownload(new Blob([serializeCwd(doc)], { type: "application/json" }), name);
}

export type ExportFormat = "png" | "jpeg";

/** Render the finished grid at source-image resolution and download it. */
export function exportImage(
  doc: Cwd,
  image: HTMLImageElement,
  format: ExportFormat,
  fileName: string | null,
): void {
  const w = image.naturalWidth;
  const h = image.naturalHeight;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not create an export canvas");
  const viewport = computeViewport(w, h, w, h); // scale 1, no offset
  if (format === "jpeg") {
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, h);
  }
  renderScene(ctx, { doc, viewport, image, selection: null, mode: "normal", showChrome: false });

  const mime = format === "jpeg" ? "image/jpeg" : "image/png";
  const ext = format === "jpeg" ? ".jpg" : ".png";
  const base = stripExtension(fileName ?? "crossword");
  canvas.toBlob(
    (blob) => {
      if (blob) triggerDownload(blob, base + ext);
    },
    mime,
    0.95,
  );
}

function stripExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(0, dot) : name;
}

function ensureExtension(name: string, ext: string): string {
  return name.toLowerCase().endsWith(ext) ? name : stripExtension(name) + ext;
}
