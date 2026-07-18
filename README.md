# gridfill

Detect a crossword grid's layout from a scanned image or PDF and save it as a
`.cwd` document (JSON: the source image plus the detected grid state) ready to
be filled in.

## Standalone executable

No Python install needed. Prebuilt Windows, macOS, and Linux executables are
attached to each [release](../../releases). Drag a scan or PDF onto the
executable, or run it from a terminal (see **Usage**).

The macOS build is unsigned, so Gatekeeper will refuse to open it with a
plain double-click the first time; right-click the executable and choose
**Open** instead, then confirm in the dialog that appears.

## Usage

```bash
gridfill scan.png              # writes scan.cwd next to the input
gridfill scan.pdf              # a PDF also works; its last page is used
gridfill scan.png -o out.cwd   # choose the output path
```

`gridfill` detects the grid(s) in the image and writes a `.cwd` document — the
source image plus the detected grid layout. There is no automatic letter
recognition; the document holds the empty grid ready to be filled in.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for installing from source, using the
Python API, building the executable, and running tests.
