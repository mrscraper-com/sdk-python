"""Custom exceptions for the MrScraper SDK."""

from __future__ import annotations


class MrScraperError(Exception):
    """Base exception for all MrScraper SDK errors."""


class AuthenticationError(MrScraperError):
    """Raised when the API token is invalid or missing."""


class APIError(MrScraperError):
    """Raised when the MrScraper API returns an error response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NetworkError(MrScraperError):
    """Raised when a network-level error occurs (timeout, connection failure, etc.)."""
