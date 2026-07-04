# CLAUDE.md

Guidance for working in this repo.

## What this is

A Python library and interactive editor for detecting a crossword grid's layout
(blocked or barred) from a scanned image and letting a person fill it in by hand —
click a cell, type letters, highlight cells, add free-text annotations — then save
the result as an image or CSV. Public API: `edit_grid()` in `crossword_transcriber`.
There is no automatic letter recognition; all cell content is entered manually.

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
