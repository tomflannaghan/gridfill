# CLAUDE.md

Guidance for working in this repo.

## What this is

A Python library and interactive editor for detecting a crossword grid's layout
(blocked or barred) from a scanned image or PDF and letting a person fill it in
by hand — click a cell, type letters, highlight cells, add free-text
annotations — then save progress as a `.cwd` document (JSON: base64 source
image + grid state) or export the result as an image. PDF input uses the last
page, rendered at 300 DPI (print quality at A4). Public API: `edit_grid()` in
`inkwell`. There is no automatic letter recognition; all cell
content is entered manually.

## Dev environment & commands

Uses `uv` with a local `.venv`.

```bash
uv venv && uv pip install -e ".[dev]"   # core + dev tools
source .venv/bin/activate                # activate before running tools

pytest                                    # tests
ruff check src tests                      # lint
ruff format src tests                     # format (run before committing)
mypy src                                  # type check (strict)
```
