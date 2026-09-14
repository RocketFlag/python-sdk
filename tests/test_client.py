import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from rocketflag import (
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


def test_env_must_be_alphanumeric():
    client = create_client()
    with pytest.raises(ValueError, match="alphanumeric"):
        client.get_flag("abc", {"env": "prod-1"})


def test_network_error():
    client = create_client(api_url="http://127.0.0.1:1")
    with pytest.raises(NetworkError):
        client.get_flag("abc123")
