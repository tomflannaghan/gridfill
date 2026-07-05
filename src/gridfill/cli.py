"""Command-line entry point for the interactive grid editor."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gridfill", description="Interactively edit a grid overlaid on its image."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help=(
            "Path to the grid image, a PDF (its last page is used), or a .cwd "
            "document saved by a previous session. Omit to start with a blank "
            "editor and use File > Open."
        ),
    )
    parser.add_argument("-o", "--out", help="Default output path for exporting the rendered image.")
    parser.add_argument("--font", help="Path to a TrueType font file.")

    args = parser.parse_args(argv)

    from .editor import edit_grid

    edit_grid(
        args.path,
        out_path=args.out,
        font_path=args.font,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
