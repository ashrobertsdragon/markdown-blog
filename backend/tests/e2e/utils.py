import time

import requests


def wait_for_server(url: str, timeout: float = 5.0) -> None:
    """Block until server responds or timeout expires."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            requests.get(url, timeout=0.5)
            return
        except requests.exceptions.RequestException:
            time.sleep(0.25)

    raise RuntimeError(f"Server did not become ready at {url}")
