# RocketFlag Python SDK

Official Python SDK for [RocketFlag](https://rocketflag.app). Same evaluation API as the [Node](https://github.com/RocketFlag/node-sdk) and [Go](https://github.com/RocketFlag/go-sdk) SDKs: create a client, fetch a flag, branch on `flag.enabled`.

## Installation

```bash
pip install rocketflag
```

Python 3.9+. No third-party runtime dependencies.

Until the package is on PyPI:

```bash
pip install git+https://github.com/RocketFlag/python-sdk.git
```

## Basic usage

```python
from rocketflag import create_client

rocketflag = create_client()  # default API URL and version (v1)

flag = rocketflag.get_flag("IFldMzqP5jtv9wAL")
if flag.enabled:
    render_new_dashboard()
else:
    render_legacy_dashboard()
```

You can also construct `Client` directly:

```python
from rocketflag import Client

client = Client()
flag = client.get_flag("IFldMzqP5jtv9wAL")
```

### Custom version or API URL

```python
rocketflag = create_client("v2", "https://your-api-domain.com")
```

## Cohorts and environment

```python
flag = rocketflag.get_flag("IFldMzqP5jtv9wAL", {
    "cohort": "beta",
    "env": "prod",
})
```

`env` must be alphanumeric, matching the Node SDK.

## Caching

Opt-in in-memory cache, keyed by flag ID **and** user context. Same behaviour as Node/Go.

```python
# Cache flag responses for 5 minutes.
rocketflag = create_client(ttl_seconds=300)

flag = rocketflag.get_flag("IFldMzqP5jtv9wAL", {"cohort": "beta"})

# Force a fresh fetch.
flag = rocketflag.get_flag("IFldMzqP5jtv9wAL", ttl_seconds=0)

# Shorter TTL for one call.
flag = rocketflag.get_flag("IFldMzqP5jtv9wAL", ttl_seconds=10)
```

Without a client default or per-call TTL, every call hits the API. The cache has no size cap; entries expire on the next lookup after TTL.

## Errors

```python
from rocketflag import APIError, InvalidResponseError, NetworkError, create_client

rocketflag = create_client()

try:
    flag = rocketflag.get_flag("IFldMzqP5jtv9wAL")
except APIError as err:
    print(f"API Error: {err.status} {err.status_text}")
except InvalidResponseError as err:
    print(f"Invalid Response Error: {err}")
except NetworkError as err:
    print(f"Network Error: {err}")
```

- `APIError` — non-OK HTTP status (includes `status` / `status_text`). A `404` means the flag ID is unknown.
- `InvalidResponseError` — body is not JSON or not a flag object (`name`, `enabled`, `id`).
- `NetworkError` — connection failure.

## Response

A successful call returns a `Flag`:

```python
Flag(name="The user-created flag name", enabled=True, id="asklWQQZdslhfsszZWkj")
```

The HTTP API may also return:

1. `200` with that object
2. `404` — flag ID not found
3. `500` — rare server error; RocketFlag is alerted

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
```
