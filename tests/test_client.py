import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from rocketflag import (
    DEFAULT_MAX_CACHE_ENTRIES,
    APIError,
    Client,
    Flag,
    InvalidResponseError,
    NetworkError,
    create_client,
)


class FlagHandler(BaseHTTPRequestHandler):
    responses = {}
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        parsed = urlparse(self.path)
        body, status = self.responses.get(parsed.path, (b"{}", 404))
        if callable(body):
            body, status = body(parsed)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@pytest.fixture
def server():
    FlagHandler.hits = 0
    FlagHandler.responses = {}
    httpd = HTTPServer(("127.0.0.1", 0), FlagHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    yield f"http://{host}:{port}", FlagHandler
    httpd.shutdown()
    httpd.server_close()


def flag_json(**overrides):
    payload = {"name": "signup", "enabled": True, "id": "abc123"}
    payload.update(overrides)
    return json.dumps(payload).encode()


def test_get_flag_success(server):
    base, handler = server
    handler.responses["/v1/flags/abc123"] = (flag_json(), 200)
    client = create_client(api_url=base)
    flag = client.get_flag("abc123")
    assert flag == Flag(name="signup", enabled=True, id="abc123")
    assert flag.enabled is True


def test_passes_context_as_query_string(server):
    base, handler = server
    seen = {}

    def body(parsed):
        seen["query"] = parse_qs(parsed.query)
        return flag_json(), 200

    handler.responses["/v1/flags/abc123"] = (body, 200)
    client = Client(api_url=base)
    client.get_flag("abc123", {"cohort": "beta", "env": "prod"})
    assert seen["query"]["cohort"] == ["beta"]
    assert seen["query"]["env"] == ["prod"]


def test_cache_hits_on_second_call(server):
    base, handler = server
    handler.responses["/v1/flags/abc123"] = (flag_json(), 200)
    client = create_client(api_url=base, ttl_seconds=60)
    first = client.get_flag("abc123", {"cohort": "beta"})
    second = client.get_flag("abc123", {"cohort": "beta"})
    assert first == second
    assert handler.hits == 1


def test_ttl_zero_bypasses_cache(server):
    base, handler = server
    handler.responses["/v1/flags/abc123"] = (flag_json(), 200)
    client = create_client(api_url=base, ttl_seconds=60)
    client.get_flag("abc123")
    client.get_flag("abc123", ttl_seconds=0)
    assert handler.hits == 2


def test_api_error_on_404(server):
    base, handler = server
    handler.responses["/v1/flags/missing"] = (b"not found", 404)
    client = create_client(api_url=base)
    with pytest.raises(APIError) as exc:
        client.get_flag("missing")
    assert exc.value.status == 404


def test_invalid_json(server):
    base, handler = server
    handler.responses["/v1/flags/abc123"] = (b"not-json", 200)
    client = create_client(api_url=base)
    with pytest.raises(InvalidResponseError):
        client.get_flag("abc123")


def test_invalid_shape(server):
    base, handler = server
    handler.responses["/v1/flags/abc123"] = (b'{"name": 1}', 200)
    client = create_client(api_url=base)
    with pytest.raises(InvalidResponseError):
        client.get_flag("abc123")


def test_requires_flag_id():
    client = create_client()
    with pytest.raises(ValueError):
        client.get_flag("")


class StubResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return flag_json()


class StubOpener:
    """Answers every request with a flag, recording the URLs it was asked for."""

    def __init__(self):
        self.urls = []

    def open(self, request):
        self.urls.append(request.full_url)
        return StubResponse()


def test_passes_targeting_key_and_audience_attributes(server):
    base, handler = server
    seen = {}

    def body(parsed):
        seen["query"] = parse_qs(parsed.query, keep_blank_values=True)
        return flag_json(), 200

    handler.responses["/v1/flags/abc123"] = (body, 200)
    client = Client(api_url=base)
    client.get_flag("abc123", {"targetingKey": "user-42", "plan": "pro", "country": "AU", "seats": 5, "beta": True})
    assert seen["query"] == {
        "targetingKey": ["user-42"],
        "plan": ["pro"],
        "country": ["AU"],
        "seats": ["5"],
        "beta": ["true"],
    }


def test_none_value_is_rejected():
    opener = StubOpener()
    client = Client(opener=opener)
    with pytest.raises(ValueError, match="Invalid value for key: plan"):
        client.get_flag("abc", {"plan": None})
    assert opener.urls == []


@pytest.mark.parametrize("env", ["prod", "prod-portals", "staging_v2", "production1"])
def test_env_accepts_letters_numbers_hyphens_and_underscores(env):
    opener = StubOpener()
    client = Client(opener=opener)
    client.get_flag("abc", {"env": env})
    assert opener.urls == [f"https://api.rocketflag.app/v1/flags/abc?env={env}"]


@pytest.mark.parametrize("env", ["prod 1", "prod.1", "prod!", "prod\n", "", True, 5])
def test_env_rejects_other_characters(env):
    opener = StubOpener()
    client = Client(opener=opener)
    with pytest.raises(ValueError, match="env values may only contain letters, numbers, hyphens and underscores"):
        client.get_flag("abc", {"env": env})
    assert opener.urls == []


def test_cache_evicts_least_recently_used_when_full():
    opener = StubOpener()
    client = Client(ttl_seconds=60, max_entries=2, opener=opener)
    client.get_flag("abc", {"targetingKey": "a"})
    client.get_flag("abc", {"targetingKey": "b"})
    client.get_flag("abc", {"targetingKey": "a"})  # hit, so "b" is now least recently used
    assert len(opener.urls) == 2

    client.get_flag("abc", {"targetingKey": "c"})  # evicts "b"
    client.get_flag("abc", {"targetingKey": "a"})
    assert len(opener.urls) == 3

    client.get_flag("abc", {"targetingKey": "b"})
    assert len(opener.urls) == 4


def test_cache_holds_10000_entries_by_default():
    assert DEFAULT_MAX_CACHE_ENTRIES == 10_000
    opener = StubOpener()
    client = Client(ttl_seconds=60, opener=opener)
    for i in range(10_001):
        client.get_flag("abc", {"targetingKey": f"user-{i}"})
    assert len(opener.urls) == 10_001

    client.get_flag("abc", {"targetingKey": "user-10000"})
    assert len(opener.urls) == 10_001
    client.get_flag("abc", {"targetingKey": "user-0"})
    assert len(opener.urls) == 10_002


def test_cache_is_safe_under_concurrent_use():
    opener = StubOpener()
    client = Client(ttl_seconds=60, max_entries=8, opener=opener)
    errors = []

    def worker(n):
        try:
            for i in range(500):
                client.get_flag("abc", {"targetingKey": f"user-{(n * i) % 20}"})
        except Exception as exc:  # pragma: no cover - surfaced by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(client._cache) <= 8


@pytest.mark.parametrize("max_entries", [0, -1, 1.5, True, "10"])
def test_max_entries_must_be_a_positive_integer(max_entries):
    with pytest.raises(ValueError, match="max_entries must be a positive integer"):
        Client(max_entries=max_entries)


def test_create_client_passes_max_entries():
    with pytest.raises(ValueError, match="max_entries must be a positive integer"):
        create_client(max_entries=0)


def test_network_error():
    client = create_client(api_url="http://127.0.0.1:1")
    with pytest.raises(NetworkError):
        client.get_flag("abc123")
