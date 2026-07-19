import { describe, it, expect } from "vitest";
import { bgrToHex, bgrToCss, hexToBgr } from "../colour.ts";

describe("BGR <-> CSS colour conversion", () => {
  it("converts a BGR triple to #rrggbb (swapping channel order)", () => {
    // BGR yellow = [0, 255, 255] -> RGB #ffff00
    expect(bgrToHex([0, 255, 255])).toBe("#ffff00");
    // BGR [255, 0, 0] is blue -> #0000ff
    expect(bgrToHex([255, 0, 0])).toBe("#0000ff");
  });

  it("converts a BGR triple to rgb(...)", () => {
    expect(bgrToCss([0, 255, 255])).toBe("rgb(255, 255, 0)");
  });

  it("round-trips #rrggbb through BGR", () => {
    expect(bgrToHex(hexToBgr("#123456"))).toBe("#123456");
    expect(hexToBgr("#ffff00")).toEqual([0, 255, 255]);
  });

  it("rejects malformed hex", () => {
    expect(() => hexToBgr("nope")).toThrow();
  });
});
