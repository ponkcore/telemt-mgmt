"""Exception hierarchy for telemt API errors.

All telemt API failures are raised as one of these typed exceptions,
enabling callers to handle network, auth, and not-found cases distinctly.
"""

from __future__ import annotations


class TelemtAPIError(Exception):
    """Base exception for all telemt API errors."""


class TelemtConnectionError(TelemtAPIError):
    """Raised when a network error prevents reaching the telemt API."""


class TelemtAuthError(TelemtAPIError):
    """Raised when the telemt API returns 401 or 403 (auth/forbidden)."""


class TelemtNotFoundError(TelemtAPIError):
    """Raised when the telemt API returns 404 (resource not found)."""
