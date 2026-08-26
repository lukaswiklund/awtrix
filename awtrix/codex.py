"""Codex plan usage via the supported local app-server protocol."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import time

from .claude import fmt_until
from .config import (
    CODEX_COMMAND,
    CODEX_ICON,
    CODEX_INTERVAL,
    CODEX_RPC_TIMEOUT,
    CODEX_USAGE_BACKOFF_MAX,
    CODEX_USAGE_POLL,
    CODEX_WINDOW_COLORS,
    COLORS,
    log,
)


def _extract_windows(result: dict) -> dict:
    """Normalize Codex's primary/secondary quota windows by their duration.

    Most plans expose a short window and a seven-day window. Some plans expose
    only one of them, so use the documented duration instead of assuming that
    primary always means short and secondary always means weekly.
    """
    bucket = result.get("rateLimits")
    if not bucket:
        bucket = (result.get("rateLimitsByLimitId") or {}).get("codex")
    if not bucket:
        return {}

    windows = {}
    for field in ("primary", "secondary"):
        raw = bucket.get(field)
        if not raw or raw.get("usedPercent") is None:
            continue
        try:
            duration = int(raw.get("windowDurationMins") or 0)
            pct = float(raw["usedPercent"])
        except (TypeError, ValueError):
            continue

        # A day is safely between Codex's rolling-hours and weekly windows.
        key = "week" if duration >= 24 * 60 else "short"
        windows[key] = {
            "pct": pct,
            "resets_at": raw.get("resetsAt"),
        }
    return windows


def fetch_codex_usage() -> dict | None:
    """Fetch ChatGPT quota windows from ``codex app-server`` over JSONL."""
    try:
        proc = subprocess.Popen(
            [CODEX_COMMAND, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as e:
        log.warning("cannot start Codex app-server: %s", e)
        return None

    messages = (
        {
            "method": "initialize",
            "id": 0,
            "params": {
                "clientInfo": {
                    "name": "awtrix",
                    "title": "AWTRIX usage bridge",
                    "version": "1.0",
                }
            },
        },
        {"method": "initialized", "params": {}},
        {"method": "account/rateLimits/read", "id": 1},
    )

    response = None
    error = "no response"
    try:
        assert proc.stdin is not None and proc.stdout is not None
        for message in messages:
            proc.stdin.write((json.dumps(message) + "\n").encode())
        proc.stdin.flush()

        deadline = time.monotonic() + CODEX_RPC_TIMEOUT
        buffered = b""
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        try:
            while time.monotonic() < deadline:
                ready = selector.select(deadline - time.monotonic())
                if not ready:
                    error = "timed out"
                    break
                chunk = os.read(proc.stdout.fileno(), 64 * 1024)
                if not chunk:
                    error = f"exited with status {proc.poll()}"
                    break
                buffered += chunk
                while b"\n" in buffered:
                    line, buffered = buffered.split(b"\n", 1)
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if message.get("id") != 1:
                        continue
                    if message.get("error"):
                        rpc_error = message["error"]
                        error = str(rpc_error.get("message") or rpc_error)
                    else:
                        response = message.get("result") or {}
                    break
                if response is not None or error != "no response":
                    break
        finally:
            selector.close()
    except (OSError, ValueError) as e:
        error = str(e)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    if response is None:
        log.warning("Codex usage fetch failed: %s", error)
        return None

    windows = _extract_windows(response)
    if not windows:
        log.warning("Codex usage response had no quota windows")
        return None
    return windows


_poll: dict = {"at": 0.0, "wait": 0.0, "data": None}


def codex_usage() -> dict | None:
    """Plan-limit percentages, polled sparsely and cached between renders."""
    now = time.time()
    if now - _poll["at"] >= _poll["wait"]:
        fresh = fetch_codex_usage()
        _poll["at"] = now
        if fresh:
            _poll.update(wait=CODEX_USAGE_POLL, data=fresh)
        else:
            backoff = _poll["wait"] * 2 if _poll["wait"] else CODEX_USAGE_POLL
            _poll["wait"] = min(backoff, CODEX_USAGE_BACKOFF_MAX)
            log.info("retrying Codex usage in %ds", _poll["wait"])

    if not _poll["data"]:
        return None

    windows = {}
    for key, window in _poll["data"].items():
        resets_at = window["resets_at"]
        if resets_at and now >= resets_at:
            windows[key] = {"pct": 0.0, "resets_at": None}
        else:
            windows[key] = dict(window)
    return windows


def _window_app(window: dict, key: str) -> dict:
    pct = max(0, min(100, round(window["pct"])))
    bar_colour = "#00E000" if pct < 60 else "#FFD000" if pct < 85 else "#FF3030"
    text = [{"t": f"{pct}%", "c": CODEX_WINDOW_COLORS[key].lstrip("#")}]
    until = fmt_until(window.get("resets_at"))
    if until:
        text.append({"t": f" {until}", "c": "808080"})

    payload = {
        "text": text,
        "textCase": 2,
        "progress": pct,
        "progressC": bar_colour,
        "progressBC": "#202020",
        "lifetime": CODEX_INTERVAL * 3,
        "lifetimeMode": 0,
    }
    if CODEX_ICON:
        payload["icon"] = CODEX_ICON
    return payload


def render_codex(usage) -> dict | None:
    """The short Codex window, or a visible error before the first success."""
    if usage is None:
        return {
            "text": "CX?",
            "color": COLORS["error"],
            "textCase": 2,
            "lifetime": 3600,
            "lifetimeMode": 0,
        }
    if "short" not in usage:
        return None
    if round(usage["short"]["pct"]) <= 0:
        return None
    return _window_app(usage["short"], "short")


def render_codex_week(usage) -> dict | None:
    """The weekly Codex window, deleted when the plan does not expose one."""
    if not usage or "week" not in usage:
        return None
    if round(usage["week"]["pct"]) <= 0:
        return None
    return _window_app(usage["week"], "week")
