"""HTTP backend: detect a grid in an uploaded image or PDF and return it as a
``.cwd`` document, for the web editor (which otherwise has no backend and can
only open a `.cwd` already on disk).

Wraps the same pipeline as the CLI (``load_image -> binarize -> detect_grids
-> document JSON``); see [cli.py](cli.py). No persistence, no auth. Runs locally
alongside the frontend dev server, or in production behind a reverse proxy,
where it also serves the built frontend (``--static-dir``) and does its own rate
limiting of the expensive detection endpoint.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .detection import detect_grids
from .document import document_to_json
from .errors import GridfillError
from .io import load_image
from .preprocess import binarize, to_grayscale

# Suffixes load_image (via cv2.imread) or the PDF branch can actually handle.
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".pdf"}

# Detection is CPU- and memory-heavy, and this backend shares a box with other
# services, so we cap how many detections run at once. Extra requests queue
# behind the limit (the per-client rate limit bounds how many can pile up). Set
# in main().
_MAX_CONCURRENCY = 1
_slots_semaphore: asyncio.Semaphore | None = None


def _slots() -> asyncio.Semaphore:
    """The shared concurrency limiter, created lazily so it binds to the running
    event loop rather than whichever loop happened to be current at import."""
    global _slots_semaphore
    if _slots_semaphore is None:
        _slots_semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
    return _slots_semaphore


class _RateLimiter:
    """Per-client token bucket: a sustained ``per_minute`` rate, plus ``burst``
    extra requests for interactive use. Only touched from the event loop, so it
    needs no lock."""

    # How often to forget clients whose buckets have refilled, in seconds.
    _SWEEP_INTERVAL = 60.0

    def __init__(self, per_minute: float, burst: int) -> None:
        self._per_second = per_minute / 60
        self._capacity = float(burst + 1)
        # client -> (tokens left, time they were counted)
        self._buckets: dict[str, tuple[float, float]] = {}
        self._last_sweep = 0.0

    def _refilled(self, tokens: float, then: float, now: float) -> float:
        return min(self._capacity, tokens + (now - then) * self._per_second)

    def retry_after(self, client: str, now: float) -> float:
        """Take a token for ``client``. Returns 0 if the request may proceed, or
        else how many seconds until it could."""
        if now - self._last_sweep >= self._SWEEP_INTERVAL:
            self._last_sweep = now
            self._buckets = {
                key: (tokens, then)
                for key, (tokens, then) in self._buckets.items()
                if self._refilled(tokens, then, now) < self._capacity
            }

        tokens, then = self._buckets.get(client, (self._capacity, now))
        tokens = self._refilled(tokens, then, now)
        if tokens < 1:
            self._buckets[client] = (tokens, now)
            return (1 - tokens) / self._per_second
        self._buckets[client] = (tokens - 1, now)
        return 0.0


# 20 detections a minute per client, with a burst of 10: detection is expensive
# (a PDF is rendered at 300 DPI first), so sustained use is deliberately low.
_rate_limiter = _RateLimiter(per_minute=20, burst=10)


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


@app.middleware("http")
async def _rate_limit_detection(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Reject over-limit detections with a 429. This is middleware, not part of
    the endpoint, because FastAPI parses the whole multipart upload before
    calling an endpoint or its dependencies.

    Registered before the CORS middleware so that CORS wraps it and a browser on
    another origin can read the 429's error message."""
    if request.method == "POST" and request.url.path == "/api/detect":
        # request.client is the real client behind the proxy; see main().
        client = request.client.host if request.client else "unknown"
        wait = _rate_limiter.retry_after(client, time.monotonic())
        if wait > 0:
            return JSONResponse(
                {"detail": "Too many detection requests. Please wait and try again."},
                status_code=429,
                headers={"Retry-After": str(math.ceil(wait))},
            )
    return await call_next(request)


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


def _mount_frontend(directory: Path) -> None:
    """Serve the built web editor at ``/``. Call after the API routes are
    registered, since a mount at the root matches everything after it.

    ``check_dir=False`` because the backend may be deployed before the frontend
    has been uploaded; the site just returns 404 until it is."""
    app.mount("/", StaticFiles(directory=directory, html=True, check_dir=False), name="frontend")


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(
        prog="gridfill-server",
        description="Run the gridfill HTTP backend for the web editor.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=1,
        help="Maximum simultaneous detections (default: 1); extra requests queue.",
    )
    parser.add_argument(
        "--static-dir",
        type=Path,
        help="Directory of the built web editor to serve at / (default: API only).",
    )
    args = parser.parse_args()

    global _MAX_CONCURRENCY
    _MAX_CONCURRENCY = args.max_concurrency

    if args.static_dir is not None:
        _mount_frontend(args.static_dir)

    # Take the client address from X-Forwarded-For when the connection comes
    # from a proxy on loopback, so the rate limit is per real client rather than
    # one bucket for the proxy. Uvicorn uses the rightmost untrusted entry, which
    # the proxy appended itself, so a client can't spoof it.
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
    )


if __name__ == "__main__":
    main()
