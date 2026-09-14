#!/usr/bin/env python3
"""End-to-end demo: evaluate a live RocketFlag via the Python SDK."""

from rocketflag import APIError, InvalidResponseError, NetworkError, create_client

FLAG_ID = "01ecwHSL0eOCfy5ufzEP"


def main() -> None:
    client = create_client()
    print(f"API: {client.api_url}/{client.version}")
    print(f"Flag ID: {FLAG_ID}")
    try:
        flag = client.get_flag(FLAG_ID)
    except APIError as err:
        raise SystemExit(f"API error: {err.status} {err.status_text}") from err
    except InvalidResponseError as err:
        raise SystemExit(f"Invalid response: {err}") from err
    except NetworkError as err:
        raise SystemExit(f"Network error: {err}") from err

    print(f"name: {flag.name}")
    print(f"id: {flag.id}")
    print(f"enabled: {flag.enabled}")
    if flag.enabled:
        print("branch: NEW path")
    else:
        print("branch: LEGACY path")


if __name__ == "__main__":
    main()
