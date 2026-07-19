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

## HTTP backend

```bash
uv pip install -e ".[server]"
gridfill-server                # serves http://127.0.0.1:8420
```

Exposes the same detection as the CLI over HTTP for the web editor: `POST
/api/detect` with a multipart `file` (image or PDF) returns a `.cwd` document
as JSON. See [server.py](src/gridfill/server.py).

## Python API

```python
from gridfill import detect_grids, save_document
```

See [../DEVELOPMENT.md](../DEVELOPMENT.md) for installing from source, the API,
and running tests.
