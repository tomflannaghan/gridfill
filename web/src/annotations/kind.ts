/** The behaviour every annotation kind provides. Rendering, hit-testing, moving
 * and geometry editing all go through this interface so no call site needs to
 * know about individual kinds — see registry.ts. */

import type { Viewport } from "../canvas/viewport.ts";
import type { Point } from "../model/geometry.ts";
import { bgrToCss } from "../model/colour.ts";
import type { Annotation } from "./types.ts";

/** A draggable editing handle: a control point the user can grab to reshape the
 * annotation. `id` is stable within a single annotation. */
export interface Handle {
  id: string;
  /** Source-image pixel position. */
  point: Point;
}

export interface AnnotationKind<A extends Annotation = Annotation> {
  /** Draw the annotation onto the canvas. */
  render(ctx: CanvasRenderingContext2D, vp: Viewport, a: A): void;
  /** True if canvas point (cx, cy) is over the annotation. */
  hitTest(ctx: CanvasRenderingContext2D, vp: Viewport, a: A, cx: number, cy: number): boolean;
  /** Selection bounds in canvas pixels, as [x, y, width, height]. */
  bounds(ctx: CanvasRenderingContext2D, vp: Viewport, a: A): [number, number, number, number];
  /** The editable control points, or [] if the kind has none. */
  handles(a: A): Handle[];
  /** Translate the whole annotation by a pixel delta. */
  moveBy(a: A, dx: number, dy: number): A;
  /** Move one handle (by its id) to a new pixel point. */
  moveHandle(a: A, handleId: string, point: Point): A;
}

/** CSS colour an annotation is drawn in (its own BGR, else the default black). */
export function annotationColour(colour: Annotation["colour"]): string {
  return colour ? bgrToCss(colour) : "#000000";
}
