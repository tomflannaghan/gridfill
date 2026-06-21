"""Command-line entry point for quick read/write demos."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crossword-transcriber")
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read", help="Transcribe a filled grid image to text.")
    p_read.add_argument("image", help="Path to the filled-grid scan.")

    p_write = sub.add_parser("write", help="Write letters into an empty grid image.")
    p_write.add_argument("image", help="Path to the empty-grid image.")
    p_write.add_argument("letters", help="Path to a text/JSON file of letters.")
    p_write.add_argument("-o", "--out", required=True, help="Output image path.")

    args = parser.parse_args(argv)

    if args.command == "read":
        from .reader import read_grid

        grid = read_grid(args.image)
        for row in grid:
            print("".join((c if c else ".") if c is not None else "#" for c in row))
        return 0

    if args.command == "write":
        print("write: not yet implemented", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
