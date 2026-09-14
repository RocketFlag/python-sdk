"""Errors raised by the RocketFlag Python SDK."""


class RocketFlagError(Exception):
    """Base class for SDK errors."""


class NetworkError(RocketFlagError):
    """Raised when the request fails to reach the API."""


class APIError(RocketFlagError):
    """Raised when the API returns a non-OK HTTP status."""

    def __init__(self, message: str, status: int, status_text: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.status_text = status_text


class InvalidResponseError(RocketFlagError):
    """Raised when the API response is not a valid flag object."""
