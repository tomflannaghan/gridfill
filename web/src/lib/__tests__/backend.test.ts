import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { detectFromImage } from "../backend.ts";

/** jsdom never actually decodes an image; simulate `onload` firing so
 * `decodeDocumentImage` (which the real Image element drives) resolves. */
class FakeImage {
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  naturalWidth = 100;
  naturalHeight = 200;
  set src(_value: string) {
    queueMicrotask(() => this.onload?.());
  }
}

function cwdResponseBody(): string {
  return JSON.stringify({
    format: "gridfill",
    version: 2,
    image: { encoding: "png", data: "" },
    grids: [],
    annotations: [],
  });
}

describe("detectFromImage", () => {
  beforeEach(() => {
    vi.stubGlobal("Image", FakeImage);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the file to the backend and loads the returned .cwd document", async () => {
    const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
      expect(url).toContain("/api/detect");
      const body = init.body as FormData;
      expect(body.get("file")).toBeInstanceOf(File);
      return new Response(cwdResponseBody(), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const file = new File(["fake-bytes"], "scan.png", { type: "image/png" });
    const loaded = await detectFromImage(file);

    expect(loaded.fileName).toBe("scan.cwd");
    expect(loaded.width).toBe(100);
    expect(loaded.height).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("surfaces the backend's error detail on a non-OK response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "No valid grid found in image" }), {
            status: 422,
          }),
      ),
    );

    const file = new File(["fake-bytes"], "scan.png", { type: "image/png" });
    await expect(detectFromImage(file)).rejects.toThrow("No valid grid found in image");
  });

  it("gives a helpful message when the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );

    const file = new File(["fake-bytes"], "scan.png", { type: "image/png" });
    await expect(detectFromImage(file)).rejects.toThrow(/backend/i);
  });
});
