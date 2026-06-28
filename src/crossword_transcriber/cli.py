"""Command-line entry point for quick read/write demos."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crossword-transcriber")
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read", help="Transcribe a filled grid image to text.")
    p_read.add_argument("image", help="Path to the filled-grid scan.")
    p_read.add_argument("--model", help="Path to ONNX model weights for letter recognition.")
    p_read.add_argument(
        "--debug-dir", help="Save each cell image and its preprocessed 28x28 to this directory."
    )

    p_write = sub.add_parser("write", help="Write letters into an empty grid image.")
    p_write.add_argument("image", help="Path to the empty-grid image.")
    p_write.add_argument("letters", help="Path to a JSON file of letters (list of lists).")
    p_write.add_argument("-o", "--out", required=True, help="Output image path.")

    args = parser.parse_args(argv)

    if args.command == "read":
        from .reader import read_grid
        from .recognize import LetterClassifier

        classifier: LetterClassifier | None = None
        if args.model:
            from .recognize.cnn import CnnLetterClassifier

            classifier = CnnLetterClassifier(args.model)

        grid = read_grid(args.image, classifier=classifier, debug_dir=args.debug_dir)
        for row in grid:
            print("".join((c if c else ".") if c is not None else "#" for c in row))
        return 0

    if args.command == "write":
        from .writer import write_grid

        with open(args.letters) as f:
            letters = json.load(f)
        write_grid(args.image, letters, out_path=args.out)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
