"""Exception types raised by the pipeline."""

from __future__ import annotations


class GridfillError(Exception):
    """Base class for all library errors."""


class GridDetectionError(GridfillError):
    """Raised when no crossword grid could be located in an image."""


class GridSegmentationError(GridfillError):
    """Raised when a detected grid could not be split into cells."""


class MultipleGridsError(GridDetectionError):
    """Raised when multiple grids are detected but no grid_index was specified."""

    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(
            f"Found {count} grids in image; specify grid_index (1-{count}) to select one"
        )


class DocumentError(GridfillError):
    """Raised when a saved ``.cwd`` document is missing, malformed, or unreadable."""
