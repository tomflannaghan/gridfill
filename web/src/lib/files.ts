/** Loading and saving files, entirely client-side (no backend).
 *
 * Open: read a `.cwd` file's text, parse it, and decode its embedded image.
 * Save: serialize the document and download it as a `.cwd`.
 * Export: render the filled grid (no editor chrome) to a PNG download.
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

/** Decode a document's embedded image, ready to hand to the store. Shared by
 * `openCwdFile` and by auto-save restoration on startup (lib/autosave.ts). */
export async function decodeDocumentImage(
  doc: Cwd,
): Promise<{ image: HTMLImageElement; width: number; height: number }> {
  const image = await decodeImage(imageDataUri(doc.image));
  return { image, width: image.naturalWidth, height: image.naturalHeight };
}

/** Parse a `.cwd` File and decode its image, ready to hand to the store. */
export async function openCwdFile(file: File): Promise<LoadedDocument> {
  const text = await file.text();
  const doc = parseCwd(text);
  const { image, width, height } = await decodeDocumentImage(doc);
  return { doc, image, width, height, fileName: file.name };
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

/** Render the finished grid at source-image resolution and download it as a PNG. */
export function exportImage(doc: Cwd, image: HTMLImageElement, fileName: string | null): void {
  const w = image.naturalWidth;
  const h = image.naturalHeight;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not create an export canvas");
  const viewport = computeViewport(w, h, w, h); // scale 1, no offset
  renderScene(ctx, { doc, viewport, image, selection: null, mode: "normal", showChrome: false });

  const base = stripExtension(fileName ?? "crossword");
  canvas.toBlob((blob) => {
    if (blob) triggerDownload(blob, base + ".png");
  }, "image/png");
}

function stripExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(0, dot) : name;
}

function ensureExtension(name: string, ext: string): string {
  return name.toLowerCase().endsWith(ext) ? name : stripExtension(name) + ext;
}
