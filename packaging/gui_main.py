"""PyInstaller entry point: run the ``gridfill`` CLI.

A plain script (rather than pointing PyInstaller at the console entry point)
so a file dropped onto the packaged executable is picked up as the path to
convert.
"""

from __future__ import annotations

import sys

from gridfill.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
