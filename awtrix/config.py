"""Settings, thresholds and palettes.

Everything tunable lives here as a literal -- edit this file to change
behaviour. Only the device address and the Dexcom credentials come from the
environment (a .env in the project root is loaded first; real environment
variables win over it), so they stay out of the source.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = PROJECT_ROOT / "icons"

load_dotenv(PROJECT_ROOT / ".env")

log = logging.getLogger("awtrix")

# ------------------------------------------------------------------ device ----

# The device's address on the LAN. Required: transport.py cannot guess it.
AWTRIX_IP = os.environ.get("AWTRIX_IP")

# ------------------------------------------------------------------ dexcom ----

# Kept optional so --selftest runs without credentials; Dexcom._connect()
# raises a clear error if they are missing when a real fetch is attempted.
DEXCOM_USERNAME = os.environ.get("DEXCOM_USERNAME")
DEXCOM_PASSWORD = os.environ.get("DEXCOM_PASSWORD")
DEXCOM_REGION = "ous"                                      # us | ous | jp

# Thresholds are in UNITS. Set UNITS = "mgdl" to switch, and rescale these.
UNITS = "mmol"
URGENT_LOW = 3.0
LOW = 3.9
HIGH = 10.0
URGENT_HIGH = 13.9

BG_INTERVAL = 60
STALE_AFTER = 900                                          # 15 min

# ------------------------------------------------------------------ claude ----

# Plan usage comes from the account endpoint Claude Code itself calls to fill
# `cachedUsageUtilization` in ~/.claude.json, authenticated with the OAuth
# token Claude Code stores in the login keychain. Undocumented and internal:
# if it ever changes shape the app falls back to showing "CC?".
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
USAGE_POLL = 300
# The endpoint is rate-limited and shared with Claude Code itself, so a failed
# poll waits longer each time (doubling from USAGE_POLL) instead of retrying at
# the normal cadence -- asking again every five minutes is how a 429 stays a
# 429. A success resets it. Capped so a transient outage still recovers within
# the hour without a restart.
USAGE_BACKOFF_MAX = 3600
CREDS_KEYCHAIN = "Claude Code-credentials"
CREDS_FILE = os.path.expanduser("~/.claude/.credentials.json")
CLAUDE_INTERVAL = 60
# Two apps rather than one: "24% 2h13 19%w" runs past 32px and scrolls, which
# leaves the 5h percent off-screen half the time. The device cycles frames
# anyway, so each window gets its own.
CLAUDE_APP = "claude"
CLAUDE_WEEK_APP = "claudew"

# ------------------------------------------------------- icons and colours ----

# 8x8 droplets on the device's /ICONS, one per range. Keys match COLORS.
# Set BG_ICON to pin one icon instead (e.g. "32045", the LaMetric blood drop).
BG_ICONS = {
    "urgent_low": "bgvlow",
    "low": "bglow",
    "in_range": "bgok",
    "high": "bghigh",
    "urgent_high": "bgvhigh",
    "stale": "bgstale",
}
BG_ICON = None
CLAUDE_ICON = None

COLORS = {
    "urgent_low": "#FF0000",
    "low": "#FF6600",
    "in_range": "#00E000",
    "high": "#FFD000",
    "urgent_high": "#FF3030",
    "stale": "#606060",
    "error": "#FF00FF",
}

# pydexcom trend_direction -> ASCII arrow. The AWTRIX bitmap font has no
# Unicode arrows, so "↗" would render as garbage.
ARROWS = {
    "DoubleUp": "^^",
    "SingleUp": "^",
    "FortyFiveUp": "/",
    "Flat": "-",
    "FortyFiveDown": "\\",
    "SingleDown": "v",
    "DoubleDown": "vv",
    "None": "",
    "NotComputable": "?",
    "RateOutOfRange": "!",
}
