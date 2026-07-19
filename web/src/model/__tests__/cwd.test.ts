import { describe, it, expect } from "vitest";
import { parseCwd, serializeCwd, imageDataUri, CwdParseError, type Cwd } from "../cwd.ts";

// A 1x1 transparent PNG.
const PNG_1x1 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

function sampleDoc(): Cwd {
  return {
    format: "gridfill",
    version: 2,
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
              [50, 0],
              [50, 100],
              [0, 100],
            ],
            kind: "letter",
            letter: "A",
            background: [0, 255, 255],
            textColour: [0, 0, 200],
            centre: [25, 50],
            size: 40,
          },
          {
            polygon: [
              [50, 0],
              [100, 0],
              [100, 100],
              [50, 100],
            ],
            kind: "empty",
            letter: null,
            background: null,
            textColour: null,
            centre: null,
            size: null,
          },
        ],
      },
      {
        type: "irregular",
        cells: [
          {
            polygon: [
              [10, 10],
              [20, 10],
              [15, 20],
            ],
            kind: "empty",
            letter: null,
            background: null,
            textColour: null,
            centre: null,
            size: null,
          },
        ],
      },
    ],
    annotations: [
      { id: "a1", type: "text", colour: null, x: 30, y: 40, text: "note", fontSize: null },
      { id: "a2", type: "text", colour: [0, 0, 255], x: 60, y: 70, text: "red note", fontSize: 18 },
      { id: "a3", type: "line", colour: null, points: [[10, 10], [40, 20]] },
      { id: "a4", type: "curve", colour: [10, 20, 30], points: [[10, 10], [20, 30], [40, 25]] },
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
    expect(payload.annotations[0]).toEqual({ type: "text", x: 30, y: 40, text: "note" });
    expect(payload.annotations[2]).toEqual({ type: "line", points: [[10, 10], [40, 20]] });
  });

  it("persists a text annotation's font size, omitting it when null", () => {
    const doc = sampleDoc();
    const payload = JSON.parse(serializeCwd(doc));
    expect(payload.annotations[0].font_size).toBeUndefined();
    expect(payload.annotations[1].font_size).toBe(18);
  });

  it("rejects an unknown annotation type", () => {
    const bad = JSON.stringify({
      format: "gridfill",
      version: 2,
      image: { encoding: "png", data: PNG_1x1 },
      grids: [],
      annotations: [{ type: "sparkle", x: 10, y: 20 }],
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
      version: 2,
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
      version: 2,
      image: { encoding: "png", data: PNG_1x1 },
      grids: [
        {
          type: "irregular",
          cells: [
            {
              polygon: [
                [10, 10],
                [20, 10],
                [15, 20],
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
    expect(doc.grids[0]!.cells[0]!.textColour).toBeNull();
  });

  it("rejects a document version that predates pixel coordinates", () => {
    // No migration path: version 1 documents stored normalized [0, 1]
    // coordinates rather than source-image pixels, so silently loading one
    // would misinterpret every coordinate rather than fail loudly.
    const v1 = JSON.stringify({
      format: "gridfill",
      version: 1,
      image: { encoding: "png", data: PNG_1x1 },
      grids: [],
      annotations: [],
    });
    expect(() => parseCwd(v1)).toThrow(CwdParseError);
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
