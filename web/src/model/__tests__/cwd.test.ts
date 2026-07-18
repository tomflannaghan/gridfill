import { describe, it, expect } from "vitest";
import { parseCwd, serializeCwd, imageDataUri, CwdParseError, type Cwd } from "../cwd.ts";

// A 1x1 transparent PNG.
const PNG_1x1 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

function sampleDoc(): Cwd {
  return {
    format: "gridfill",
    version: 1,
    image: { encoding: "png", data: PNG_1x1 },
    grids: [
      {
        type: "rectangular",
        rows: 1,
        cols: 2,
        cells: [
          {
            polygon: [
              [0, 0],
              [0.5, 0],
              [0.5, 1],
              [0, 1],
            ],
            kind: "letter",
            letter: "A",
            background: [0, 255, 255],
            textColor: [0, 0, 200],
            centre: [0.25, 0.5],
          },
          {
            polygon: [
              [0.5, 0],
              [1, 0],
              [1, 1],
              [0.5, 1],
            ],
            kind: "empty",
            letter: null,
            background: null,
            textColor: null,
            centre: null,
          },
        ],
      },
      {
        type: "irregular",
        cells: [
          {
            polygon: [
              [0.1, 0.1],
              [0.2, 0.1],
              [0.15, 0.2],
            ],
            kind: "empty",
            letter: null,
            background: null,
            textColor: null,
            centre: null,
          },
        ],
      },
    ],
    annotations: [
      { id: "a1", type: "text", color: null, x: 0.3, y: 0.4, text: "note" },
      { id: "a2", type: "text", color: [0, 0, 255], x: 0.6, y: 0.7, text: "red note" },
      { id: "a3", type: "line", color: null, points: [[0.1, 0.1], [0.4, 0.2]] },
      { id: "a4", type: "curve", color: [10, 20, 30], points: [[0.1, 0.1], [0.2, 0.3], [0.4, 0.25]] },
    ],
  };
}

/** Annotation ids are regenerated on load, so blank them before comparing. */
function withoutIds(doc: Cwd): Cwd {
  return { ...doc, annotations: doc.annotations.map((a) => ({ ...a, id: "" })) };
}

describe("parseCwd / serializeCwd", () => {
  it("round-trips a document losslessly (ids aside)", () => {
    const doc = sampleDoc();
    const reparsed = parseCwd(serializeCwd(doc));
    expect(withoutIds(reparsed)).toEqual(withoutIds(doc));
  });

  it("assigns each parsed annotation a fresh, unique id", () => {
    const reparsed = parseCwd(serializeCwd(sampleDoc()));
    const ids = reparsed.annotations.map((a) => a.id);
    expect(ids.every((id) => id.length > 0)).toBe(true);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("omits a default (null) colour on disk", () => {
    const doc = sampleDoc();
    const payload = JSON.parse(serializeCwd(doc));
    expect(payload.annotations[0]).toEqual({ type: "text", x: 0.3, y: 0.4, text: "note" });
    expect(payload.annotations[2]).toEqual({ type: "line", points: [[0.1, 0.1], [0.4, 0.2]] });
  });

  it("rejects an unknown annotation type", () => {
    const bad = JSON.stringify({
      format: "gridfill",
      version: 1,
      image: { encoding: "png", data: PNG_1x1 },
      grids: [],
      annotations: [{ type: "sparkle", x: 0.1, y: 0.2 }],
    });
    expect(() => parseCwd(bad)).toThrow(CwdParseError);
  });

  it("preserves the embedded image bytes unchanged", () => {
    const doc = sampleDoc();
    const reparsed = parseCwd(serializeCwd(doc));
    expect(reparsed.image.data).toBe(PNG_1x1);
  });

  it("accepts legacy format magics", () => {
    const legacy = JSON.stringify({
      format: "inkwell",
      version: 1,
      image: { encoding: "png", data: PNG_1x1 },
      grids: [],
      annotations: [],
    });
    const doc = parseCwd(legacy);
    expect(doc.format).toBe("gridfill"); // normalized on load
  });

  it("defaults text colour for documents predating the field", () => {
    const legacy = JSON.stringify({
      format: "gridfill",
      version: 1,
      image: { encoding: "png", data: PNG_1x1 },
      grids: [
        {
          type: "irregular",
          cells: [
            {
              polygon: [
                [0.1, 0.1],
                [0.2, 0.1],
                [0.15, 0.2],
              ],
              kind: "letter",
              letter: "A",
              background: null,
              centre: null,
            },
          ],
        },
      ],
      annotations: [],
    });
    const doc = parseCwd(legacy);
    expect(doc.grids[0]!.cells[0]!.textColor).toBeNull();
  });

  it("rejects non-gridfill JSON", () => {
    expect(() => parseCwd(JSON.stringify({ hello: "world" }))).toThrow(CwdParseError);
    expect(() => parseCwd("not json")).toThrow(CwdParseError);
  });

  it("builds a usable data URI", () => {
    expect(imageDataUri({ encoding: "png", data: PNG_1x1 })).toBe(
      `data:image/png;base64,${PNG_1x1}`,
    );
  });
});
