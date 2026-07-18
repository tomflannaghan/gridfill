/** Colour conversions.
 *
 * `.cwd` cell backgrounds are stored as OpenCV **BGR** integer triples (see
 * `Cell.to_dict` in python/src/gridfill/types.py), so every hop between the
 * document model and the browser (CSS / <input type=color>, which are RGB)
 * must swap the channel order. Keep that swap here and nowhere else.
 */

export type Bgr = [number, number, number];

const clamp = (v: number): number => Math.max(0, Math.min(255, Math.round(v)));
const hex2 = (v: number): string => clamp(v).toString(16).padStart(2, "0");

/** BGR triple -> CSS "#rrggbb". */
export function bgrToHex([b, g, r]: Bgr): string {
  return `#${hex2(r)}${hex2(g)}${hex2(b)}`;
}

/** BGR triple -> CSS "rgb(r, g, b)". */
export function bgrToCss([b, g, r]: Bgr): string {
  return `rgb(${clamp(r)}, ${clamp(g)}, ${clamp(b)})`;
}

/** CSS "#rrggbb" (as produced by <input type=color>) -> BGR triple. */
export function hexToBgr(hex: string): Bgr {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex.trim());
  if (!m) throw new Error(`Not a #rrggbb colour: ${hex}`);
  const r = parseInt(m[1]!, 16);
  const g = parseInt(m[2]!, 16);
  const b = parseInt(m[3]!, 16);
  return [b, g, r];
}

/** The editor's default highlight colour (yellow), in BGR. */
export const DEFAULT_HIGHLIGHT_BGR: Bgr = [0, 255, 255];
