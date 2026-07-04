"""PyInstaller entry point: launch the editor like ``crossword-transcriber edit``.

A plain script (rather than pointing PyInstaller at the console entry point)
so a file dropped onto the packaged executable is picked up as the path to
open, and so the app launches windowed with no console.
"""

from __future__ import annotations

import sys

from crossword_transcriber.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["edit", *sys.argv[1:]]))
