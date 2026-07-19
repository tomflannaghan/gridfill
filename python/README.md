# gridfill

Detect a crossword grid's layout from a scanned image or PDF and save it as a
`.cwd` document (JSON: the source image plus the detected grid state) ready to
be filled in.

This is the Python library and CLI. It lives in the [`python/`](.) directory of
the [gridfill monorepo](../README.md); the browser editor for `.cwd` documents
is in [`web/`](../web).

## Usage

```bash
gridfill scan.png              # writes scan.cwd next to the input
gridfill scan.pdf              # a PDF also works; its last page is used
gridfill scan.png -o out.cwd   # choose the output path
```

`gridfill` detects the grid(s) in the image and writes a `.cwd` document — the
source image plus the detected grid layout. There is no automatic letter
recognition; the document holds the empty grid ready to be filled in.

## Python API

```python
from gridfill import detect_grids, save_document
```

See [../DEVELOPMENT.md](../DEVELOPMENT.md) for installing from source, the API,
and running tests.
