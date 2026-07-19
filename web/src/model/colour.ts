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

/** The editor's default text colour (black), in BGR. */
export const DEFAULT_TEXT_BGR: Bgr = [0, 0, 0];

/** True if a BGR triple is the default text colour (black). Content painted in
 * the default colour is persisted as `null`, keeping documents clean. */
export function isBlack([b, g, r]: Bgr): boolean {
  return b === 0 && g === 0 && r === 0;
}

/** The colour to persist for content painted in `bgr`: null for the default
 * black (so untouched documents stay free of colour noise), else a copy. */
export function persistedColour(bgr: Bgr): Bgr | null {
  return isBlack(bgr) ? null : ([...bgr] as Bgr);
}

/** A readable foreground (black or white) for an icon/glyph drawn over a swatch
 * filled with `bgr`, picked by perceptual luminance. */
export function contrastFg([b, g, r]: Bgr): string {
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.6 ? "#000000" : "#ffffff";
}
