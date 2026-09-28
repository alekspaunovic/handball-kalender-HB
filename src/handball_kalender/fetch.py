"""Netzwerk-Fetch der Quell-Feeds (SPEC.md Abschnitt 11)."""

from __future__ import annotations

import requests


def fetch_ics(url: str, timeout: float = 30.0) -> bytes:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content
