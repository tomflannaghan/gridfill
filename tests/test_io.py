"""Tests for image/PDF loading via load_image()."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from crossword_transcriber.io import load_image

Image.init()  # eagerly register plugins; PdfImagePlugin needs JPEG's registered lazily otherwise


def _save_pdf(
    path: Path, colors: list[tuple[int, int, int]], size: tuple[int, int] = (100, 100)
) -> None:
    pages = [Image.new("RGB", size, color) for color in colors]
    pages[0].save(path, save_all=True, append_images=pages[1:])


def test_load_image_reads_last_page_of_multi_page_pdf(tmp_path: Path) -> None:
    path = tmp_path / "doc.pdf"
    _save_pdf(path, [(255, 0, 0), (0, 255, 0)])

    image = load_image(path)

    # BGR green, the last page. Pillow's PDF plugin re-encodes as JPEG, so allow
    # a little compression rounding rather than requiring an exact match.
    b, g, r = (int(c) for c in image[0, 0])
    assert b < 10
    assert g > 245
    assert r < 10


def test_load_image_single_page_pdf(tmp_path: Path) -> None:
    path = tmp_path / "doc.pdf"
    _save_pdf(path, [(0, 0, 255)])

    image = load_image(path)

    b, g, r = (int(c) for c in image[0, 0])  # BGR red
    assert b > 245
    assert g < 10
    assert r < 10


def test_load_image_pdf_renders_at_print_resolution(tmp_path: Path) -> None:
    # An A4-sized page (595x842 pt) should render near standard 300 DPI pixel dims.
    path = tmp_path / "a4.pdf"
    _save_pdf(path, [(255, 255, 255)], size=(595, 842))

    image = load_image(path)

    height, width = image.shape[:2]
    assert width > 2400
    assert height > 3400


def test_load_image_missing_pdf_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_image(tmp_path / "missing.pdf")
