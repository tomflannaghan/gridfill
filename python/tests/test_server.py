"""Tests for the HTTP backend (server.py)."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

import gridfill.server as server
from gridfill.server import app
from tests.synthetic import make_grid

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give each test its own budget, so tests don't throttle one another."""
    monkeypatch.setattr(server, "_rate_limiter", server._RateLimiter(per_minute=20, burst=10))


def _png_bytes(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def test_detect_returns_cwd_document_for_grid_image() -> None:
    grid = make_grid()
    response = client.post(
        "/api/detect",
        files={"file": ("scan.png", _png_bytes(grid.image), "image/png")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    payload = response.json()
    assert set(payload) == {"format", "version", "image", "grids", "annotations"}
    assert payload["format"] == "gridfill"
    assert len(payload["grids"]) == 1
    assert payload["grids"][0]["rows"] == grid.n_rows
    assert payload["grids"][0]["cols"] == grid.n_cols
    assert payload["annotations"] == []


def test_detect_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/api/detect",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_detect_returns_422_when_no_grid_found() -> None:
    blank = np.full((200, 200, 3), 255, dtype=np.uint8)
    response = client.post(
        "/api/detect",
        files={"file": ("blank.png", _png_bytes(blank), "image/png")},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("filename", ["scan", "scan.gif", "scan.doc"])
def test_detect_rejects_missing_or_unknown_extension(filename: str) -> None:
    response = client.post(
        "/api/detect",
        files={"file": (filename, b"not an image", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_detect_serializes_concurrent_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the default limit of 1, overlapping requests must not run detection
    at the same time — the guard that stops this heavy work swamping the box."""
    monkeypatch.setattr(server, "_MAX_CONCURRENCY", 1)
    monkeypatch.setattr(server, "_slots_semaphore", None)

    real_detect = server.detect_grids
    lock = threading.Lock()
    state = {"active": 0, "peak": 0}

    def instrumented(binary: np.ndarray):  # type: ignore[no-untyped-def]
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        try:
            time.sleep(0.05)  # widen the window so any overlap is observed
            return real_detect(binary)
        finally:
            with lock:
                state["active"] -= 1

    monkeypatch.setattr(server, "detect_grids", instrumented)
    png = _png_bytes(make_grid().image)

    async def hammer() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            return await asyncio.gather(
                *(
                    ac.post("/api/detect", files={"file": ("scan.png", png, "image/png")})
                    for _ in range(4)
                )
            )

    responses = asyncio.run(hammer())

    assert all(r.status_code == 200 for r in responses)
    assert state["peak"] == 1


def _post_unsupported(headers: dict[str, str] | None = None) -> httpx.Response:
    """A cheap request that still counts against the limit (400, no detection)."""
    return client.post(
        "/api/detect",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=headers,
    )


def test_rate_limiter_allows_burst_then_refills_at_the_sustained_rate() -> None:
    limiter = server._RateLimiter(per_minute=20, burst=10)

    assert all(limiter.retry_after("a", 0.0) == 0 for _ in range(11))
    assert limiter.retry_after("a", 0.0) == pytest.approx(3.0)
    # One token takes 3s to come back at 20/minute, and only one is available.
    assert limiter.retry_after("a", 3.0) == 0
    assert limiter.retry_after("a", 3.0) > 0


def test_rate_limiter_tracks_clients_separately() -> None:
    limiter = server._RateLimiter(per_minute=20, burst=0)

    assert limiter.retry_after("a", 0.0) == 0
    assert limiter.retry_after("a", 0.0) > 0
    assert limiter.retry_after("b", 0.0) == 0


def test_rate_limiter_forgets_clients_once_their_buckets_refill() -> None:
    limiter = server._RateLimiter(per_minute=20, burst=0)

    limiter.retry_after("a", 0.0)
    limiter.retry_after("b", 1000.0)

    assert set(limiter._buckets) == {"b"}


def test_detect_returns_429_with_retry_after_when_over_limit() -> None:
    assert all(_post_unsupported().status_code == 400 for _ in range(11))

    response = _post_unsupported()

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1
    assert isinstance(response.json()["detail"], str)  # the editor displays this


def test_rate_limited_response_is_readable_cross_origin() -> None:
    """The dev frontend is on another origin; without CORS headers on the 429 it
    would see a network failure rather than the message."""
    origin = {"Origin": "http://localhost:5173"}
    for _ in range(11):
        _post_unsupported(origin)

    response = _post_unsupported(origin)

    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == "*"


@pytest.fixture
def mounted_frontend(tmp_path: Path) -> Iterator[None]:
    (tmp_path / "index.html").write_text("<title>Gridfill Editor</title>")
    (tmp_path / "app.js").write_text("console.log(1)")
    routes_before = list(app.router.routes)
    server._mount_frontend(tmp_path)
    yield
    app.router.routes[:] = routes_before


@pytest.mark.usefixtures("mounted_frontend")
def test_frontend_is_served_alongside_the_api() -> None:
    assert "Gridfill Editor" in client.get("/").text
    assert client.get("/app.js").status_code == 200
    # The root mount must not shadow the API.
    assert _post_unsupported().status_code == 400


@pytest.mark.usefixtures("mounted_frontend")
def test_static_requests_are_not_rate_limited() -> None:
    assert all(client.get("/app.js").status_code == 200 for _ in range(30))
