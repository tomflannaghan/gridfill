"""HTTP backend: detect a grid in an uploaded image or PDF and return it as a
``.cwd`` document, for the web editor (which otherwise has no backend and can
only open a `.cwd` already on disk).

Wraps the same pipeline as the CLI (``load_image -> binarize -> detect_grids
-> document JSON``); see [cli.py](cli.py). No persistence, no auth -- intended
for local/single-user use alongside the frontend dev server.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .detection import detect_grids
from .document import document_to_json
from .errors import GridfillError
from .io import load_image
from .preprocess import binarize, to_grayscale

# Suffixes load_image (via cv2.imread) or the PDF branch can actually handle.
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".pdf"}

# Detection is CPU- and memory-heavy, and this backend shares a small box with
# other services, so we cap how many detections run at once. Extra requests
# queue behind the limit (nginx bounds how many can pile up). Set in main().
_MAX_CONCURRENCY = 1
_slots_semaphore: asyncio.Semaphore | None = None


def _slots() -> asyncio.Semaphore:
    """The shared concurrency limiter, created lazily so it binds to the running
    event loop rather than whichever loop happened to be current at import."""
    global _slots_semaphore
    if _slots_semaphore is None:
        _slots_semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
    return _slots_semaphore


def _detect_document(data: bytes, suffix: str) -> str:
    """Blocking pipeline: raw upload bytes -> detected ``.cwd`` JSON. Runs in a
    worker thread (see :func:`detect`) so the heavy CV work never blocks the
    event loop; raises ``GridfillError``/``OSError`` for the caller to map."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        image = load_image(path)
        binary = binarize(to_grayscale(image))
        grids = detect_grids(binary)
    finally:
        os.unlink(path)
    return document_to_json(image, grids, [])


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

    # Hold a slot across the whole request, and only read the upload into memory
    # once we have one, so queued requests don't each buffer a full image.
    async with _slots():
        data = await file.read()
        try:
            content = await run_in_threadpool(_detect_document, data, suffix)
        except GridfillError as exc:
            raise HTTPException(422, str(exc)) from None
        except OSError as exc:
            raise HTTPException(400, str(exc)) from None

    return Response(content=content, media_type="application/json")


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(
        prog="gridfill-server",
        description="Run the gridfill HTTP backend for the web editor.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=1,
        help="Maximum simultaneous detections (default: 1); extra requests queue.",
    )
    args = parser.parse_args()

    global _MAX_CONCURRENCY
    _MAX_CONCURRENCY = args.max_concurrency

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
