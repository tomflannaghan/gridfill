# gridfill web editor

A purely-frontend React + TypeScript app for editing `.cwd` documents (the
crossword layouts produced by the [gridfill](../python) Python tool) in the
browser: it overlays the detected grid on its source image and lets you fill it
in by hand, highlight cells, and add text annotations. No backend — files are
opened and saved entirely client-side.

See [editor.md](editor.md) for the full intended behaviour.

## Develop

```bash
npm install
npm run dev        # start the Vite dev server
npm test           # run the Vitest unit tests
npm run typecheck  # strict TypeScript check
npm run build      # production build to dist/
```

Open a `.cwd` file with **File → Open** (or drag one onto the window). Generate
one from the Python CLI, e.g. `cd ../python && uv run gridfill scan.png`.

## Layout

- `src/model/` — the `.cwd` document model and pure logic: `cwd.ts`
  (parse/serialize), `grid.ts` (navigation, ported from the Python `types.py`),
  `geometry.ts`, `color.ts` (BGR↔RGB — cell colours are stored OpenCV-style BGR).
- `src/state/store.ts` — editor state (document, selection, mode, highlight) and
  every editing mutation, as a zustand store.
- `src/canvas/` — the canvas surface: `viewport.ts` (image↔canvas transform),
  `render.ts` (drawing), `hitTest.ts`, and the `CanvasEditor` component.
- `src/ui/` — the menu bar, colour picker, inline annotation editor, context menu.
- `src/lib/files.ts` — open / save `.cwd` and export PNG/JPEG.

### Coordinates & colours

Cell polygon vertices and annotation positions are stored as `[0, 1]` fractions
of the **source image** size (decode the embedded PNG to get its pixel
dimensions). Cell/highlight colours are OpenCV **BGR** triples — convert via
`src/model/color.ts` for anything CSS. On save the embedded image bytes are
re-written unchanged for a loss-free round-trip.
