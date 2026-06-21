# crossword-transcriber

Read handwritten crossword grids from images into a 2D array of letters, and write
a letter array back into an empty grid image.

> Status: **early scaffold.** Core types and the package skeleton are in place; the
> pipeline stages are stubbed. See [PLAN.md](PLAN.md) for the design and roadmap.

## Install (development)

```bash
uv venv
uv pip install -e ".[dev]"
# For the handwriting-recognition backend (Phase 4):
uv pip install -e ".[dev,recognize]"
```

## Usage (target API)

```python
from crossword_transcriber import read_grid, write_grid

# Read: scan -> list[list[str | None]]
#   None = block cell, "" = empty white cell, "A".."Z" = recognised letter
grid = read_grid("filled.png")

# Write: empty grid + letters -> filled image
write_grid("empty.png", grid, out_path="filled_out.png")
```

## Scope (v1)

Clean scans; square uniform grids (blocked **and** barred); single uppercase A-Z
letters; fully offline. See [PLAN.md](PLAN.md) for details.

## Development

```bash
ruff check . && ruff format --check .
mypy src
pytest
```
