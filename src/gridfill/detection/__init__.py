"""Grid detection.

Rectangular grids (``detect_grid``/``detect_grids``) are detected off an
axis-aligned line lattice; irregular grids (``detect_irregular_grids``) are
detected by segmenting enclosed cell regions and work for any cell shape.
"""

from __future__ import annotations

from .combined import detect_grids
from .irregular import detect_irregular_grids
from .rectangle import detect_grid, detect_rectangular_grids

__all__ = [
    "detect_grid",
    "detect_grids",
    "detect_rectangular_grids",
    "detect_irregular_grids",
]
