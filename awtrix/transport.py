"""HTTP to the AWTRIX device. Every push goes through here."""

from __future__ import annotations

import requests

from .config import AWTRIX_IP, log


def _post(path: str, payload, params=None) -> bool:
    if not AWTRIX_IP:
        log.warning("AWTRIX_IP is unset -- set it in .env; dropping push to %s", path)
        return False
    url = f"http://{AWTRIX_IP}/api/{path}"
    try:
        r = requests.post(url, json=payload, params=params, timeout=5)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("push to %s failed: %s", path, e)
        return False


def push_app(name: str, payload: dict | None) -> bool:
    """Send a custom app. payload=None deletes it."""
    return _post("custom", payload if payload is not None else {}, {"name": name})


def notify(payload: dict) -> bool:
    return _post("notify", payload)


def indicator(n: int, payload: dict) -> bool:
    return _post(f"indicator{n}", payload)
