"""Shared reading-order sorting for detected grid features."""

from __future__ import annotations

from typing import TypeVar

_T = TypeVar("_T")


def reading_order(items: list[tuple[float, float, _T]], band: float) -> list[_T]:
    """Sort ``(cy, cx, payload)`` items into reading order and return the payloads.

    Items are grouped into rows top-to-bottom (a new row starts whenever an
    item's ``cy`` is more than *band* below the current row's first item) and
    ordered left-to-right by ``cx`` within each row. Used for both cells within
    a grid and whole grids on a page.
    """
    ordered = sorted(items, key=lambda t: (t[0], t[1]))
    rows: list[list[tuple[float, float, _T]]] = []
    for item in ordered:
        if rows and abs(item[0] - rows[-1][0][0]) < band:
            rows[-1].append(item)
        else:
            rows.append([item])
    for row in rows:
        row.sort(key=lambda t: t[1])
    return [payload for row in rows for _, _, payload in row]
