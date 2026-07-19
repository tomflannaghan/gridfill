# CLAUDE.md — web frontend

Frontend-specific gotchas. See the repo root [CLAUDE.md](../CLAUDE.md) for
project-wide conventions (normalized coords, BGR colours, the mirrored `.cwd`
format) and [editor.md](editor.md) for the editor's intended behaviour. Run
tooling from `web/`: `npm run dev`, `npm test` (vitest), `npm run typecheck`.

## Architecture

Purely a frontend — a `.cwd` is plain JSON, so no backend is involved. The
canvas is drawn **imperatively**; React owns the chrome (toolbar, menus, inline
text editor) but not the grid pixels.

- [src/model/](src/model/) — pure, framework-free logic: `cwd.ts` (the document
  model + parse/serialize, **mirrors Python `document.py`** — keep in sync),
  `grid.ts` (cell navigation / reading order), `geometry.ts`, `color.ts` (the
  **only** place BGR↔RGB is swapped).
- [src/state/store.ts](src/state/store.ts) — the zustand store: the loaded doc,
  tool, selection, mode, and every mutation behind an [editor.md](editor.md)
  interaction. **Undo/redo = whole-document snapshots** pushed onto `past` /
  `future` (immutable + structurally shared, so snapshots are cheap); a mutation
  that should be undoable snapshots `doc` before changing it. View-only state
  (e.g. `zoomToGrid`) is deliberately *not* part of the doc and *not* undoable.
- [src/canvas/](src/canvas/) — `render.ts` (draws image → grids → annotations),
  `viewport.ts` (normalized↔canvas-pixel transforms), `hitTest.ts`,
  `CanvasEditor.tsx` (pointer/keyboard wiring).
- [src/annotations/](src/annotations/) — the annotation kinds. See below.
- [src/ui/](src/ui/) — React chrome (`Toolbar`, `MenuBar`, `AnnotationEditor`).

## Adding an annotation kind

Annotations (text/line/curve) are a **registry-driven tagged union**. Every call
site (renderer, hit-tester, pointer input) goes through the generic helpers in
[registry.ts](src/annotations/registry.ts), which dispatch on `annotation.type`
to an `AnnotationKind` implementation ([kind.ts](src/annotations/kind.ts)
defines the interface: render / hitTest / bounds / handles / moveBy /
moveHandle). To add a kind: add its variant to `types.ts`, implement an
`AnnotationKind`, and register it in `registry.ts`'s `KINDS` map — **nothing
else special-cases a kind**. Also add its JSON case to `cwd.ts` *and* Python
`document.py` (both sides of the format).

## React StrictMode + inline editors

`main.tsx` renders the app inside `<StrictMode>`, so on **every** mount React
runs the effect/mount cycle twice (mount → unmount → remount) in dev. A
component that **focuses itself on mount and commits on blur** (like the inline
`AnnotationEditor`) will self-destruct: the simulated unmount blurs the
freshly-focused input, the blur handler commits an empty value, and the editor
closes before the user can type. It looks fine in a production build (no
StrictMode) but is broken under `npm run dev`.

The fix pattern: **defer focus, and only arm the blur-commit, on the next
animation frame** — after the synchronous StrictMode churn has settled. See
`AnnotationEditor.tsx` (`requestAnimationFrame` + an `acceptBlur` ref). Reuse
this for any future focus-on-mount / commit-on-blur widget.

Unit-testable via `@testing-library/react`: assert a blur *before* the first
frame does **not** commit, and a blur *after* does. Reproduce the bug by
reverting to synchronous focus to confirm the test fails.

## Driving / inspecting the store

In dev builds (`import.meta.env.DEV`) the zustand store is exposed as
`window.__editor` (see `main.tsx`). Use `window.__editor.getState()` to read or
drive editor state from Playwright / a browser console when verifying — e.g.
`window.__editor.getState().doc.annotations`. It is not present in production
builds.

The app has no repo-committed browser-test setup; to drive the canvas end-to-end
you can launch the system Chromium (`/usr/bin/chromium-browser`) via a
temporary `npx playwright` install with `executablePath` + `--no-sandbox`, load
a `.cwd` through the hidden `input.hidden-file-input`, and dispatch pointer
events on `canvas.editor-canvas`.
