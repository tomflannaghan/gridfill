"""HTTP backend: detect a grid in an uploaded image or PDF and return it as a
``.cwd`` document, for the web editor (which otherwise has no backend and can
only open a `.cwd` already on disk).

Wraps the same pipeline as the CLI (``load_image -> binarize -> detect_grids
-> document JSON``); see [cli.py](cli.py). No persistence, no auth -- intended
for local/single-user use alongside the frontend dev server.
"""

from __future__ import annotations

import argparse
import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .detection import detect_grids
from .document import document_to_json
from .errors import GridfillError
from .io import load_image
from .preprocess import binarize, to_grayscale

# Suffixes load_image (via cv2.imread) or the PDF branch can actually handle.
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".pdf"}

app = FastAPI(
    title="gridfill",
    description="Detect crossword grids in an image or PDF and produce a .cwd document.",
)

# No auth and this only ever reads uploaded bytes back out as a document, so an
# open CORS policy is fine for a local single-user tool.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


@app.post("/api/detect")
async def detect(file: UploadFile = File(...)) -> Response:  # noqa: B008 (FastAPI DI pattern)
    """Detect the grid(s) in an uploaded image or PDF and return a ``.cwd`` document."""
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported file type: {suffix or '(none)'!r}")

    data = await file.read()
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        try:
            image = load_image(path)
            binary = binarize(to_grayscale(image))
            grids = detect_grids(binary)
        except GridfillError as exc:
            raise HTTPException(422, str(exc)) from None
        except OSError as exc:
            raise HTTPException(400, str(exc)) from None
    finally:
        os.unlink(path)

    return Response(content=document_to_json(image, grids, []), media_type="application/json")


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(
        prog="gridfill-server",
        description="Run the gridfill HTTP backend for the web editor.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8420)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
