"""Claude plan usage: OAuth token lookup, the usage endpoint, and the app payload.

The percentages are the subscription rate limits (what /usage shows), not
spend. Authentication reuses the OAuth token Claude Code already stores -- on
macOS in the login keychain, elsewhere in a plain credentials file.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime

import requests

from .config import (
    CLAUDE_ICON,
    CLAUDE_INTERVAL,
    COLORS,
    CREDS_FILE,
    CREDS_KEYCHAIN,
    USAGE_POLL,
    USAGE_URL,
    log,
)


def oauth_token() -> str | None:
    """Claude Code's OAuth access token.

    Read fresh on every poll rather than held: Claude Code rotates it, and a
    cached copy would start returning 401 a few hours in.
    """
    raw = None
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", CREDS_KEYCHAIN, "-w"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if out.returncode == 0:
            raw = out.stdout.strip()
    except (subprocess.SubprocessError, OSError) as e:
        log.debug("keychain read failed: %s", e)

    if not raw:  # non-macOS installs keep it in a plain file
        try:
            with open(CREDS_FILE) as f:
                raw = f.read()
        except OSError:
            return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return (data.get("claudeAiOauth") or data).get("accessToken")


def iso_to_epoch(value) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def fetch_usage() -> dict | None:
    """Percent of each plan limit, straight from the account endpoint."""
    token = oauth_token()
    if not token:
        log.warning("no OAuth token found; is Claude Code logged in?")
        return None

    try:
        r = requests.get(
            USAGE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
            },
            timeout=10,
        )
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError) as e:
        log.warning("usage fetch failed: %s", e)
        return None

    # The windows used to sit under "utilization"; they are top-level now, and
    # the old key still exists with a null value. Accept either shape.
    util = body.get("utilization") or body

    windows = {}
    for key in ("five_hour", "seven_day"):
        w = util.get(key)
        if not w:
            continue
        windows[key] = {
            "pct": float(w.get("utilization") or 0.0),
            "resets_at": iso_to_epoch(w.get("resets_at")),
        }

    if not windows:
        # 200 but nothing we recognise -- the endpoint is internal and may
        # have been reshaped. Log the keys so it's obvious what moved.
        log.warning("usage response had no known windows; keys=%s", list(util)[:8])
        return None
    return windows


_poll: dict = {"at": 0.0, "data": None}


def claude_usage() -> dict | None:
    """Plan-limit percentages, polled at USAGE_POLL and cached in between.

    Cached so the countdown can be re-rendered every minute without hitting
    the endpoint each time -- resets_at is absolute, so it stays correct.
    """
    now = time.time()
    if now - _poll["at"] >= USAGE_POLL:
        fresh = fetch_usage()
        if fresh:
            _poll.update(at=now, data=fresh)

    if not _poll["data"]:
        return None

    windows = {}
    for key, w in _poll["data"].items():
        resets_at = w["resets_at"]
        if resets_at and now >= resets_at:
            # Window rolled over since the last successful poll. Whatever was
            # used belonged to the old window, so start the new one at zero.
            windows[key] = {"pct": 0.0, "resets_at": None}
        else:
            windows[key] = dict(w)
    return windows


def fmt_until(resets_at) -> str | None:
    """Time left in the window, sized to fit 32px: 45m, 2h13, 3d."""
    if not resets_at:
        return None
    mins = int((resets_at - time.time()) // 60)
    if mins <= 0:
        return None
    if mins >= 1440:
        return f"{mins // 1440}d"
    if mins >= 60:
        return f"{mins // 60}h{mins % 60:02d}"
    return f"{mins}m"


def _window_app(window: dict, suffix: str = "") -> dict:
    """One window as an app payload: percent, time to reset, progress bar."""
    pct = max(0, min(100, round(window["pct"])))
    bar_colour = "#00E000" if pct < 60 else "#FFD000" if pct < 85 else "#FF3030"

    text = [{"t": f"{pct}%{suffix}", "c": bar_colour.lstrip("#")}]
    until = fmt_until(window.get("resets_at"))
    if until:
        text.append({"t": f" {until}", "c": "808080"})

    payload = {
        "text": text,
        "textCase": 2,
        "progress": pct,
        "progressC": bar_colour,
        "progressBC": "#202020",
        # Dev machine off -> app disappears rather than showing stale numbers.
        "lifetime": CLAUDE_INTERVAL * 3,
        "lifetimeMode": 0,
    }
    if CLAUDE_ICON:
        payload["icon"] = CLAUDE_ICON
    return payload


def render_claude(usage) -> dict:
    """The 5-hour window. Falls back to "CC?" so a failure stays visible."""
    if not usage or "five_hour" not in usage:
        return {
            "text": "CC?",
            "color": COLORS["error"],
            "textCase": 2,
            "lifetime": 3600,
            "lifetimeMode": 0,
        }
    return _window_app(usage["five_hour"])


def render_claude_week(usage) -> dict | None:
    """The 7-day window, marked with a trailing "w".

    None when the endpoint returned no weekly window -- the caller pushes that
    as a delete, so the frame disappears instead of freezing on an old number.
    """
    if not usage or "seven_day" not in usage:
        return None
    return _window_app(usage["seven_day"], suffix="w")
