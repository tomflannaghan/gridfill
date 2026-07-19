# gridfill

Detect a crossword grid's layout from a scanned image or PDF and save it as a
`.cwd` document (JSON: the source image plus the detected grid state) ready to
be filled in.

## Usage

```bash
gridfill scan.png              # writes scan.cwd next to the input
gridfill scan.pdf              # a PDF also works; its last page is used
gridfill scan.png -o out.cwd   # choose the output path
```

`gridfill` detects the grid(s) in the image and writes a `.cwd` document — the
source image plus the detected grid layout. There is no automatic letter
recognition; the document holds the empty grid ready to be filled in.

## Repository layout

This is a monorepo:

- [python/](python/) — the Python library and CLI described above.
- [web/](web/) — a React + TypeScript webapp (purely frontend) for editing the
  detected grid in the browser: filling cells in by hand, highlighting, and
  adding annotations. See [web/editor.md](web/editor.md).

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for installing the Python project from
source, using the Python API, and running tests.
