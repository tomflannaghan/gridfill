import { describe, it, expect, beforeEach } from "vitest";
import { saveAutosave, loadAutosave, clearAutosave, type KeyValueStore } from "../autosave.ts";
import type { Cwd } from "../../model/cwd.ts";

function fakeStore(): KeyValueStore {
  const data = new Map<string, unknown>();
  return {
    get: (key) => Promise.resolve(data.get(key)),
    set: (key, value) => {
      data.set(key, value);
      return Promise.resolve();
    },
    delete: (key) => {
      data.delete(key);
      return Promise.resolve();
    },
  };
}

function doc(): Cwd {
  return { format: "gridfill", version: 2, image: { encoding: "png", data: "abc" }, grids: [], annotations: [] };
}

describe("autosave", () => {
  let store: KeyValueStore;

  beforeEach(() => {
    store = fakeStore();
  });

  it("round-trips a saved document and its file name", async () => {
    await saveAutosave(doc(), "puzzle.cwd", store);
    const record = await loadAutosave(store);
    expect(record).toEqual({ doc: doc(), fileName: "puzzle.cwd" });
  });

  it("returns null when nothing has been saved", async () => {
    expect(await loadAutosave(store)).toBeNull();
  });

  it("overwrites the previous save rather than accumulating", async () => {
    await saveAutosave(doc(), "first.cwd", store);
    await saveAutosave({ ...doc(), annotations: [] }, "second.cwd", store);
    expect((await loadAutosave(store))?.fileName).toBe("second.cwd");
  });

  it("clears the saved document", async () => {
    await saveAutosave(doc(), "puzzle.cwd", store);
    await clearAutosave(store);
    expect(await loadAutosave(store)).toBeNull();
  });

  it("swallows storage errors on save and load", async () => {
    const broken: KeyValueStore = {
      get: () => Promise.reject(new Error("boom")),
      set: () => Promise.reject(new Error("boom")),
      delete: () => Promise.reject(new Error("boom")),
    };
    await expect(saveAutosave(doc(), null, broken)).resolves.toBeUndefined();
    await expect(loadAutosave(broken)).resolves.toBeNull();
    await expect(clearAutosave(broken)).resolves.toBeUndefined();
  });
});
