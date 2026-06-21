"""Exception types raised by the pipeline."""

from __future__ import annotations


class TranscriberError(Exception):
    """Base class for all library errors."""


class GridDetectionError(TranscriberError):
    """Raised when no crossword grid could be located in an image."""


class GridSegmentationError(TranscriberError):
    """Raised when a detected grid could not be split into cells."""
