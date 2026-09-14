"""Official Python SDK for RocketFlag."""

from .client import DEFAULT_API_URL, DEFAULT_VERSION, Client, Flag, create_client
from .errors import APIError, InvalidResponseError, NetworkError, RocketFlagError

__all__ = [
    "APIError",
    "Client",
    "DEFAULT_API_URL",
    "DEFAULT_VERSION",
    "Flag",
    "InvalidResponseError",
    "NetworkError",
    "RocketFlagError",
    "create_client",
]

__version__ = "0.1.0"
