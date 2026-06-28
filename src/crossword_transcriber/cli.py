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
    p_read.add_argument(
        "--csv",
        metavar="PATH",
        help="Save grid data (letters, colours, confidences) to a CSV file.",
    )
    p_read.add_argument(
        "--grid",
        type=int,
        metavar="INDEX",
        help="1-based index of the grid to use when the image contains multiple grids.",
    )

    p_edit = sub.add_parser("edit", help="Interactively edit a grid overlaid on its image.")
    p_edit.add_argument("image", help="Path to the grid image.")
    p_edit.add_argument(
        "--csv",
        metavar="PATH",
        help="Load initial cell data from a CSV file (from read --csv).",
    )
    p_edit.add_argument("-o", "--out", help="Default output path for saving the rendered image.")
    p_edit.add_argument("--font", help="Path to a TrueType font file.")
    p_edit.add_argument(
        "--highlight-confidence",
        type=float,
        metavar="THRESH",
        help="Highlight cells with confidence below this threshold.",
    )
    p_edit.add_argument(
        "--grid",
        type=int,
        metavar="INDEX",
        help="1-based index of the grid to use when the image contains multiple grids.",
    )

    p_write = sub.add_parser("write", help="Write letters into an empty grid image.")
    p_write.add_argument("image", help="Path to the empty-grid image.")
    p_write.add_argument(
        "letters", help="Path to a grid CSV file (from read --csv) or a JSON file of letters."
    )
    p_write.add_argument("-o", "--out", required=True, help="Output image path.")
    p_write.add_argument(
        "--highlight-confidence",
        type=float,
        metavar="THRESH",
        help="Highlight cells with confidence below this threshold.",
    )
    p_write.add_argument(
        "--grid",
        type=int,
        metavar="INDEX",
        help="1-based index of the grid to use when the image contains multiple grids.",
    )

    args = parser.parse_args(argv)

    if args.command == "read":
        from .reader import read_grid
        from .recognize import LetterClassifier

        classifier: LetterClassifier | None = None
        if args.model:
            from .recognize.cnn import CnnLetterClassifier

            classifier = CnnLetterClassifier(args.model)

        grid = read_grid(
            args.image, classifier=classifier, debug_dir=args.debug_dir, grid_index=args.grid
        )
        for row in grid.to_letters():
            print("".join((c if c else ".") if c is not None else "#" for c in row))

        if args.csv:
            grid.save_csv(args.csv)

        return 0

    if args.command == "edit":
        from .editor import edit_grid
        from .types import Grid

        edit_input: Grid | None = None
        if args.csv:
            edit_input = Grid.load_csv(args.csv)

        edit_grid(
            args.image,
            edit_input,
            out_path=args.out,
            font_path=args.font,
            highlight_confidence=args.highlight_confidence,
            grid_index=args.grid,
        )
        return 0

    if args.command == "write":
        from .types import Grid
        from .writer import write_grid

        letters_path: str = args.letters
        letters: Grid | list[list[str | None]]
        if letters_path.endswith(".csv"):
            letters = Grid.load_csv(letters_path)
        else:
            with open(letters_path) as f:
                letters = json.load(f)
        write_grid(
            args.image,
            letters,
            out_path=args.out,
            highlight_confidence=args.highlight_confidence,
            grid_index=args.grid,
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
