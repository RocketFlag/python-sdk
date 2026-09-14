"""RocketFlag evaluation client.

Mirrors the Node and Go SDKs: GET {api_url}/{version}/flags/{flag_id}
with optional query-string user context (cohort, env, …) and an opt-in
in-memory TTL cache keyed by flag ID + context.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Union

from .errors import APIError, InvalidResponseError, NetworkError

DEFAULT_API_URL = "https://api.rocketflag.app"
DEFAULT_VERSION = "v1"
_ALPHANUMERIC = re.compile(r"^[a-zA-Z0-9]+$")

ContextValue = Union[str, int, float, bool]
UserContext = Mapping[str, ContextValue]


@dataclass(frozen=True)
class Flag:
    """A evaluated feature flag."""

    name: str
    enabled: bool
    id: str


def _validate_flag(payload: Any) -> Flag:
    if not isinstance(payload, dict):
        raise InvalidResponseError("Invalid response format: response is not an object")
    name = payload.get("name")
    enabled = payload.get("enabled")
    flag_id = payload.get("id")
    if not isinstance(name, str) or not isinstance(enabled, bool) or not isinstance(flag_id, str):
        raise InvalidResponseError("Invalid response from server")
    return Flag(name=name, enabled=enabled, id=flag_id)


def _validate_context(user_context: UserContext) -> None:
    for key, value in user_context.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (str, int, float)):
            if key == "env":
                if not isinstance(value, str) or not _ALPHANUMERIC.match(value):
                    raise ValueError(f"env values must be alphanumeric. Invalid value for env: {value!r}")
            continue
        raise ValueError(
            f"userContext values must be of type str, int, float, or bool. Invalid value for key: {key}"
        )


def _cache_key(flag_id: str, params: Mapping[str, str]) -> str:
    items = sorted(params.items())
    query = urllib.parse.urlencode(items)
    return f"{flag_id}?{query}"


class Client:
    """RocketFlag API client."""

    def __init__(
        self,
        version: str = DEFAULT_VERSION,
        api_url: str = DEFAULT_API_URL,
        *,
        ttl_seconds: Optional[float] = None,
        opener: Optional[urllib.request.OpenerDirector] = None,
    ) -> None:
        self.version = version
        self.api_url = api_url.rstrip("/")
        self._default_ttl_ms = 0.0 if ttl_seconds is None else float(ttl_seconds) * 1000.0
        self._cache: dict[str, tuple[Flag, float]] = {}
        self._opener = opener or urllib.request.build_opener()

    def get_flag(
        self,
        flag_id: str,
        user_context: Optional[UserContext] = None,
        *,
        ttl_seconds: Optional[float] = None,
    ) -> Flag:
        if not flag_id:
            raise ValueError("flagId is required")
        if not isinstance(flag_id, str):
            raise TypeError("flagId must be a string")

        context: UserContext = user_context or {}
        if not isinstance(context, Mapping):
            raise TypeError("userContext must be an object")
        _validate_context(context)

        params = {key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in context.items()}
        path = f"{self.api_url}/{self.version}/flags/{urllib.parse.quote(flag_id, safe='')}"
        url = f"{path}?{urllib.parse.urlencode(params)}" if params else path

        effective_ttl_ms = self._default_ttl_ms if ttl_seconds is None else float(ttl_seconds) * 1000.0
        cache_key = ""
        if effective_ttl_ms > 0:
            cache_key = _cache_key(flag_id, params)
            entry = self._cache.get(cache_key)
            if entry is not None:
                flag, expires_at = entry
                if expires_at > time.time() * 1000.0:
                    return Flag(name=flag.name, enabled=flag.enabled, id=flag.id)
                del self._cache[cache_key]

        request = urllib.request.Request(url, method="GET")
        try:
            with self._opener.open(request) as response:
                status = getattr(response, "status", None) or response.getcode()
                if status != 200:
                    status_text = getattr(response, "reason", "") or ""
                    raise APIError(f"API request failed with status {status}", status, status_text)
                raw = response.read()
        except APIError:
            raise
        except urllib.error.HTTPError as exc:
            raise APIError(f"API request failed with status {exc.code}", exc.code, exc.reason or "") from exc
        except urllib.error.URLError as exc:
            raise NetworkError(f"Network error: {exc.reason}") from exc
        except OSError as exc:
            raise NetworkError(f"Network error: {exc}") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise InvalidResponseError("Failed to parse JSON response") from exc

        flag = _validate_flag(payload)
        if effective_ttl_ms > 0:
            self._cache[cache_key] = (flag, time.time() * 1000.0 + effective_ttl_ms)
        return flag


def create_client(
    version: str = DEFAULT_VERSION,
    api_url: str = DEFAULT_API_URL,
    ttl_seconds: Optional[float] = None,
) -> Client:
    """Create a client. Signature matches Node's createRocketflagClient(version, apiUrl, { ttlSeconds })."""
    return Client(version, api_url, ttl_seconds=ttl_seconds)
