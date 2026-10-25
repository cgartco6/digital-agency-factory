"""Shared primitives across all studios."""
from __future__ import annotations


class StudioError(RuntimeError):
    """Raised when a studio engine cannot fulfill a request."""


class ValidationFailure(StudioError):
    """Raised when upstream input fails schema or policy validation."""
