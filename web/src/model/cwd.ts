/** The `.cwd` document model and (de)serialization.
 *
 * Mirrors the Python format written by `save_document` and read by
 * `load_document` (python/src/gridfill/document.py, types.py). A `.cwd` file is
 * plain JSON, so no backend is needed to read or write it:
 *
 *   {
 *     "format": "gridfill", "version": 2,
 *     "image": { "encoding": "png", "data": "<base64 PNG>" },
 *     "grids": [ <grid>, ... ],
 *     "annotations": [
 *       { "type": "text",  "x": x, "y": y, "text": "...", "font_size": n },
 *       { "type": "line",  "points": [[x,y],[x,y]], "colour": [b,g,r] },
 *       { "type": "curve", "points": [[x,y], ...] }
 *     ]
 *   }
 *
 * Coordinates (cell polygon vertices and annotation points) are source-image
 * pixel positions. Cell `background` / `text_colour` and an annotation's
 * optional `colour` are BGR triples (omitted for the default black). A text
 * annotation's `font_size` is likewise source-image pixels, omitted for
 * documents predating the field. An annotation's in-memory `id` is not
 * persisted.
 */

import { polygonCentroid, type Point } from "./geometry.ts";
import { newAnnotationId, type Annotation } from "../annotations/types.ts";

export type { Annotation } from "../annotations/types.ts";

export type CellKind = "block" | "empty" | "letter";

export interface Cell {
  polygon: Point[];
  kind: CellKind;
  letter: string | null;
  /** OpenCV BGR triple, or null. See model/colour.ts. */
  background: [number, number, number] | null;
  /** OpenCV BGR triple the cell's letter is drawn in, or null for the default
   * (black). Persisted as `text_colour`. */
  textColour: [number, number, number] | null;
  /** The cell's incircle centre, in source-image pixels, precomputed and
   * persisted by the Python library (`polygon_incircle`). Where a glyph sits
   * best and the point navigation treats as the cell's location. Null only
   * for documents predating the field. Prefer `cellCentre()` to read it. */
  centre: Point | null;
  /** The cell's incircle diameter, in source-image pixels, precomputed and
   * persisted by the Python library (`polygon_incircle`). Recover it on
   * canvas with `imageLengthToCanvas`. The basis for the letter font size, so
   * the frontend never recomputes a distance transform itself. Null only for
   * documents predating the field. */
  size: number | null;
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
// Bumped 1 -> 2 when coordinates switched from normalized [0, 1] fractions to
// source-image pixels; version-1 documents are not supported (no migration;
// mirrors `_FORMAT_VERSION` in document.py).
const FORMAT_VERSION = 2;

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
  const tc = c.text_colour;
  const textColour = tc == null ? null : asPoint3(tc);
  return {
    polygon: (c.polygon as unknown[]).map(asPoint),
    kind,
    letter: c.letter == null ? null : String(c.letter),
    background,
    textColour,
    centre: c.centre == null ? null : asPoint(c.centre),
    size: c.size == null ? null : Number(c.size),
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
  const colour = o.colour == null ? null : asPoint3(o.colour);
  const id = newAnnotationId();
  switch (o.type) {
    case "text":
      return {
        id,
        type: "text",
        colour,
        x: Number(o.x),
        y: Number(o.y),
        text: String(o.text),
        fontSize: o.font_size == null ? null : Number(o.font_size),
      };
    case "line": {
      const pts = (o.points as unknown[]).map(asPoint);
      if (pts.length < 2) throw new CwdParseError("Line annotation needs two points");
      return { id, type: "line", colour, points: [pts[0]!, pts[1]!] };
    }
    case "curve": {
      const pts = (o.points as unknown[]).map(asPoint);
      if (pts.length < 2) throw new CwdParseError("Curve annotation needs at least two points");
      return { id, type: "curve", colour, points: pts };
    }
    default:
      throw new CwdParseError(`Unknown annotation type: ${String(o.type)}`);
  }
}

function annotationToJson(a: Annotation): unknown {
  const colour = a.colour == null ? {} : { colour: [...a.colour] };
  switch (a.type) {
    case "text":
      return {
        type: "text",
        x: a.x,
        y: a.y,
        text: a.text,
        ...(a.fontSize == null ? {} : { font_size: a.fontSize }),
        ...colour,
      };
    case "line":
      return { type: "line", points: a.points.map(([x, y]) => [x, y]), ...colour };
    case "curve":
      return { type: "curve", points: a.points.map(([x, y]) => [x, y]), ...colour };
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
  if (p.version !== FORMAT_VERSION) {
    // No migration path: versions before 2 stored normalized [0, 1]
    // coordinates rather than source-image pixels, so silently loading one
    // would misinterpret every coordinate rather than fail loudly.
    throw new CwdParseError(
      `Unsupported document version ${String(p.version)} (expected ${FORMAT_VERSION})`,
    );
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
    version: FORMAT_VERSION,
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
    text_colour: c.textColour == null ? null : [...c.textColour],
    centre: c.centre == null ? null : [c.centre[0], c.centre[1]],
    size: c.size,
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
