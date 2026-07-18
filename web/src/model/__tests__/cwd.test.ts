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
      [0.3, 0.4, "note", null],
      [0.6, 0.7, "red note", [0, 0, 255]],
    ],
  };
}

describe("parseCwd / serializeCwd", () => {
  it("round-trips a document losslessly", () => {
    const doc = sampleDoc();
    const reparsed = parseCwd(serializeCwd(doc));
    expect(reparsed).toEqual(doc);
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
      annotations: [[0.3, 0.4, "note"]], // pre-colour 3-element form
    });
    const doc = parseCwd(legacy);
    expect(doc.grids[0]!.cells[0]!.textColor).toBeNull();
    expect(doc.annotations[0]).toEqual([0.3, 0.4, "note", null]);
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
