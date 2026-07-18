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
 *     "annotations": [ [x, y, "text"], [x, y, "text", [b,g,r]], ... ]
 *   }
 *
 * Coordinates (cell polygon vertices and annotation x/y) are fractions of the
 * source image's (width, height), in [0, 1]. Cell `background` / `text_color`
 * and an annotation's optional 4th element are BGR triples.
 */

import { polygonCentroid, type Point } from "./geometry.ts";

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

/** An [x, y, text, color?] annotation; x/y are [0,1] fractions of image size.
 * `color` is the BGR text colour, or null/absent for the default (black). */
export type Annotation = [number, number, string, ([number, number, number] | null)?];

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
    ? p.annotations.map((a) => {
        const arr = a as unknown[];
        const color = arr.length > 3 && arr[3] != null ? asPoint3(arr[3]) : null;
        return [Number(arr[0]), Number(arr[1]), String(arr[2]), color];
      })
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
    annotations: doc.annotations.map(([x, y, text, color]) =>
      color == null ? [x, y, text] : [x, y, text, [...color]],
    ),
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
