"""Tests for the HTTP backend (server.py)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from gridfill.server import app
from tests.synthetic import make_grid

client = TestClient(app)


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
