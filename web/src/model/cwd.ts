/** The `.cwd` document model and (de)serialization.
 *
 * Mirrors the Python format written by `save_document` and read by
 * `load_document` (python/src/gridfill/document.py, types.py). A `.cwd` file is
 * plain JSON, so no backend is needed to read or write it:
 *
 *   {
 *     "format": "gridfill", "version": 1,
 *     "image": { "encoding": "png", "data": "<base64 PNG>" },
 *     "grids": [ <grid>, ... ],
 *     "annotations": [
 *       { "type": "text",  "x": x, "y": y, "text": "..." },
 *       { "type": "line",  "points": [[x,y],[x,y]], "color": [b,g,r] },
 *       { "type": "curve", "points": [[x,y], ...] }
 *     ]
 *   }
 *
 * Coordinates (cell polygon vertices and annotation points) are fractions of the
 * source image's (width, height), in [0, 1]. Cell `background` / `text_color`
 * and an annotation's optional `color` are BGR triples (omitted for the default
 * black). An annotation's in-memory `id` is not persisted.
 */

import { polygonCentroid, type Point } from "./geometry.ts";
import { newAnnotationId, type Annotation } from "../annotations/types.ts";

export type { Annotation } from "../annotations/types.ts";

export type CellKind = "block" | "empty" | "letter";

export interface Cell {
  polygon: Point[];
  kind: CellKind;
  letter: string | null;
  /** OpenCV BGR triple, or null. See model/color.ts. */
  background: [number, number, number] | null;
  /** OpenCV BGR triple the cell's letter is drawn in, or null for the default
   * (black). Persisted as `text_color`. */
  textColor: [number, number, number] | null;
  /** The cell's incircle centre (normalized [0,1]), precomputed and persisted
   * by the Python library (`polygon_centre`). Where a glyph sits best and the
   * point navigation treats as the cell's location. Null only for documents
   * predating the field. Prefer `cellCentre()` to read it. */
  centre: Point | null;
}

/** The cell's persisted incircle centre, falling back to the vertex mean for
 * older documents that predate the saved `centre`. */
export function cellCentre(cell: Cell): Point {
  return cell.centre ?? polygonCentroid(cell.polygon);
}

export interface RectangularGrid {
  type: "rectangular";
  rows: number;
  cols: number;
  cells: Cell[];
}

export interface IrregularGrid {
  type: "irregular";
  cells: Cell[];
}

export type Grid = RectangularGrid | IrregularGrid;

export interface Cwd {
  format: "gridfill";
  version: number;
  image: { encoding: string; data: string };
  grids: Grid[];
  annotations: Annotation[];
}

const FORMAT_MAGIC = "gridfill";
// Accepted on load so documents saved before the project's rename(s) still open
// (mirrors `_LEGACY_FORMAT_MAGICS` in document.py).
const LEGACY_FORMAT_MAGICS = new Set(["crossword-transcriber", "inkwell"]);
const FORMAT_VERSION = 1;

export class CwdParseError extends Error {}

function asPoint(v: unknown): Point {
  if (!Array.isArray(v) || v.length < 2) throw new CwdParseError("Invalid point");
  return [Number(v[0]), Number(v[1])];
}

function parseCell(raw: unknown): Cell {
  if (typeof raw !== "object" || raw === null) throw new CwdParseError("Invalid cell");
  const c = raw as Record<string, unknown>;
  const kind = c.kind;
  if (kind !== "block" && kind !== "empty" && kind !== "letter") {
    throw new CwdParseError(`Invalid cell kind: ${String(kind)}`);
  }
  const bg = c.background;
  const background = bg == null ? null : asPoint3(bg);
  const tc = c.text_color;
  const textColor = tc == null ? null : asPoint3(tc);
  return {
    polygon: (c.polygon as unknown[]).map(asPoint),
    kind,
    letter: c.letter == null ? null : String(c.letter),
    background,
    textColor,
    centre: c.centre == null ? null : asPoint(c.centre),
  };
}

function asPoint3(v: unknown): [number, number, number] {
  if (!Array.isArray(v) || v.length < 3) throw new CwdParseError("Invalid colour");
  return [Number(v[0]), Number(v[1]), Number(v[2])];
}

function parseGrid(raw: unknown): Grid {
  if (typeof raw !== "object" || raw === null) throw new CwdParseError("Invalid grid");
  const g = raw as Record<string, unknown>;
  const cells = (g.cells as unknown[]).map(parseCell);
  if (g.type === "rectangular") {
    return { type: "rectangular", rows: Number(g.rows), cols: Number(g.cols), cells };
  }
  if (g.type === "irregular") {
    return { type: "irregular", cells };
  }
  throw new CwdParseError(`Unknown grid type: ${String(g.type)}`);
}

function parseAnnotation(raw: unknown): Annotation {
  if (typeof raw !== "object" || raw === null) throw new CwdParseError("Invalid annotation");
  const o = raw as Record<string, unknown>;
  const color = o.color == null ? null : asPoint3(o.color);
  const id = newAnnotationId();
  switch (o.type) {
    case "text":
      return { id, type: "text", color, x: Number(o.x), y: Number(o.y), text: String(o.text) };
    case "line": {
      const pts = (o.points as unknown[]).map(asPoint);
      if (pts.length < 2) throw new CwdParseError("Line annotation needs two points");
      return { id, type: "line", color, points: [pts[0]!, pts[1]!] };
    }
    case "curve": {
      const pts = (o.points as unknown[]).map(asPoint);
      if (pts.length < 2) throw new CwdParseError("Curve annotation needs at least two points");
      return { id, type: "curve", color, points: pts };
    }
    default:
      throw new CwdParseError(`Unknown annotation type: ${String(o.type)}`);
  }
}

function annotationToJson(a: Annotation): unknown {
  const color = a.color == null ? {} : { color: [...a.color] };
  switch (a.type) {
    case "text":
      return { type: "text", x: a.x, y: a.y, text: a.text, ...color };
    case "line":
      return { type: "line", points: a.points.map(([x, y]) => [x, y]), ...color };
    case "curve":
      return { type: "curve", points: a.points.map(([x, y]) => [x, y]), ...color };
  }
}

/** Parse the text of a `.cwd` file into a validated document model. */
export function parseCwd(text: string): Cwd {
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch {
    throw new CwdParseError("File is not valid JSON");
  }
  if (typeof payload !== "object" || payload === null) {
    throw new CwdParseError("Not a gridfill document");
  }
  const p = payload as Record<string, unknown>;
  const format = p.format;
  if (typeof format !== "string" || (format !== FORMAT_MAGIC && !LEGACY_FORMAT_MAGICS.has(format))) {
    throw new CwdParseError("Not a gridfill document");
  }
  const image = p.image as Record<string, unknown> | undefined;
  if (!image || typeof image.data !== "string") {
    throw new CwdParseError("Document is missing its image");
  }
  const grids = Array.isArray(p.grids) ? p.grids.map(parseGrid) : [];
  const annotations: Annotation[] = Array.isArray(p.annotations)
    ? p.annotations.map(parseAnnotation)
    : [];
  return {
    format: FORMAT_MAGIC,
    version: typeof p.version === "number" ? p.version : FORMAT_VERSION,
    image: { encoding: String(image.encoding ?? "png"), data: image.data },
    grids,
    annotations,
  };
}

/** Serialize a document model back to `.cwd` JSON text.
 *
 * The embedded image (`image.data`) is written back unchanged for a loss-free
 * round-trip; the image is never re-encoded. `format` is always normalized to
 * the current magic and `version` preserved.
 */
export function serializeCwd(doc: Cwd): string {
  const payload = {
    format: FORMAT_MAGIC,
    version: doc.version,
    image: { encoding: doc.image.encoding, data: doc.image.data },
    grids: doc.grids.map(gridToJson),
    annotations: doc.annotations.map(annotationToJson),
  };
  return JSON.stringify(payload);
}

function gridToJson(grid: Grid): unknown {
  const cells = grid.cells.map((c) => ({
    polygon: c.polygon.map(([x, y]) => [x, y]),
    kind: c.kind,
    letter: c.letter,
    background: c.background == null ? null : [...c.background],
    text_color: c.textColor == null ? null : [...c.textColor],
    centre: c.centre == null ? null : [c.centre[0], c.centre[1]],
  }));
  if (grid.type === "rectangular") {
    return { type: "rectangular", rows: grid.rows, cols: grid.cols, cells };
  }
  return { type: "irregular", cells };
}

/** A `data:` URI for the embedded image, usable as an <img> src. */
export function imageDataUri(image: Cwd["image"]): string {
  const mime = image.encoding === "jpeg" || image.encoding === "jpg" ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${image.data}`;
}
