"""Common utilities for pytest that aren't fixtures."""

import socket


def has_internet():
    try:
        with socket.create_connection(("github.com", 443), timeout=2):
            return True
    except OSError:
        return False
