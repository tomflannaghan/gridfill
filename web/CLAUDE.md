# CLAUDE.md — web frontend

Frontend-specific gotchas. See the repo root `CLAUDE.md` for project-wide
guidance and [editor.md](editor.md) for the editor's intended behaviour.

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
