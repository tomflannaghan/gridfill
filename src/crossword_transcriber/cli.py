"""Command-line entry point for the interactive grid editor."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crossword-transcriber")
    sub = parser.add_subparsers(dest="command", required=True)

    p_edit = sub.add_parser("edit", help="Interactively edit a grid overlaid on its image.")
    p_edit.add_argument(
        "path",
        nargs="?",
        default=None,
        help=(
            "Path to the grid image, a PDF (its last page is used), or a .cwd "
            "document saved by a previous session. Omit to start with a blank "
            "editor and use File > Open."
        ),
    )
    p_edit.add_argument("-o", "--out", help="Default output path for exporting the rendered image.")
    p_edit.add_argument("--font", help="Path to a TrueType font file.")

    args = parser.parse_args(argv)

    if args.command == "edit":
        from .editor import edit_grid

        edit_grid(
            args.path,
            out_path=args.out,
            font_path=args.font,
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
