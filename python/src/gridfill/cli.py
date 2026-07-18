"""Command-line entry point: convert a grid image or PDF into a ``.cwd`` document."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from .detection import detect_grids
from .document import CWD_EXTENSION, save_document
from .errors import GridfillError
from .io import load_image
from .preprocess import binarize, to_grayscale


def _default_out_path(input_path: str) -> str:
    """Derive the output ``.cwd`` path from an input path (swap the extension)."""
    stem, _ = os.path.splitext(input_path)
    return stem + CWD_EXTENSION


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gridfill",
        description="Detect the grid in an image or PDF and write it as a .cwd document.",
    )
    parser.add_argument(
        "path",
        help="Path to the grid image, or a PDF (its last page is used).",
    )
    parser.add_argument(
        "-o",
        "--out",
        help=(
            "Output path for the .cwd document. Defaults to the input path with a .cwd extension."
        ),
    )

    args = parser.parse_args(argv)

    out_path = args.out or _default_out_path(args.path)

    try:
        image = load_image(args.path)
        binary = binarize(to_grayscale(image))
        grids = detect_grids(binary)
        save_document(out_path, image, grids, [])
    except (GridfillError, OSError) as exc:
        print(f"gridfill: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(grids)} grid(s) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
