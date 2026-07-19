/** Annotation data model: a discriminated union over annotation *kinds*.
 *
 * An annotation is free content drawn on top of the grid (text, lines, curves).
 * Every kind carries a stable in-memory `id` (used for selection and editing;
 * regenerated on load, never persisted) and an optional BGR `colour` (null = the
 * editor's default black). All coordinates are normalized [0,1] fractions of the
 * source image, like cell polygons — see CLAUDE.md and model/cwd.ts.
 *
 * Adding a new kind is deliberately cheap: add a variant here, a module under
 * annotations/ implementing `AnnotationKind`, register it in registry.ts, and add
 * a tool to the toolbar. Rendering, hit-testing, moving and editing all dispatch
 * through the registry, so no call site special-cases individual kinds.
 */

import type { Point } from "../model/geometry.ts";
import type { Bgr } from "../model/colour.ts";

interface BaseAnnotation {
  id: string;
  /** BGR triple the annotation is drawn in, or null for the default (black). */
  colour: Bgr | null;
}

/** Free text anchored at its top-left (x, y). */
export interface TextAnnotation extends BaseAnnotation {
  type: "text";
  x: number;
  y: number;
  text: string;
}

/** A straight line between two points. */
export interface LineAnnotation extends BaseAnnotation {
  type: "line";
  points: [Point, Point];
}

/** A smooth curve passing through its anchor points (>= 2). */
export interface CurveAnnotation extends BaseAnnotation {
  type: "curve";
  points: Point[];
}

export type Annotation = TextAnnotation | LineAnnotation | CurveAnnotation;
export type AnnotationType = Annotation["type"];

/** A fresh unique id for a new annotation. */
export function newAnnotationId(): string {
  return crypto.randomUUID();
}

export function createText(x: number, y: number, text: string, colour: Bgr | null): TextAnnotation {
  return { id: newAnnotationId(), type: "text", colour, x, y, text };
}

export function createLine(p0: Point, p1: Point, colour: Bgr | null): LineAnnotation {
  return { id: newAnnotationId(), type: "line", colour, points: [p0, p1] };
}

export function createCurve(points: Point[], colour: Bgr | null): CurveAnnotation {
  return { id: newAnnotationId(), type: "curve", colour, points };
}
