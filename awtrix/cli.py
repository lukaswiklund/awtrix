"""Argument parsing and the poll loop."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .claude import claude_usage, render_claude, render_claude_week
from .config import (
    AWTRIX_IP,
    BG_ICONS,
    BG_INTERVAL,
    CLAUDE_APP,
    CLAUDE_INTERVAL,
    CLAUDE_WEEK_APP,
    log,
)
from .dexcom import Dexcom, check_alarm, render_bg
from .icons import install_icons
from .transport import push_app


def selftest() -> None:
    """Push dummy values so the layout can be checked without credentials."""
    log.info("pushing dummy apps to %s", AWTRIX_IP)
    push_app("bg", {"text": [{"t": "5.4", "c": "00E000"}, {"t": "/", "c": "00E000"}],
                    "icon": BG_ICONS["in_range"], "textCase": 2, "center": True})
    push_app(CLAUDE_APP, {"text": [{"t": "24%", "c": "00E000"},
                                   {"t": " 2h13", "c": "808080"}],
                          "textCase": 2, "progress": 24,
                          "progressC": "#00E000", "progressBC": "#202020"})
    push_app(CLAUDE_WEEK_APP, {"text": [{"t": "67%w", "c": "FFD000"},
                                        {"t": " 3d", "c": "808080"}],
                               "textCase": 2, "progress": 67,
                               "progressC": "#FFD000", "progressBC": "#202020"})
    log.info("done — check the device")


def run(once: bool = False) -> None:
    dexcom = Dexcom()
    state: dict = {}
    next_bg = 0.0
    next_claude = 0.0

    # Older versions pushed a sparkline app; drop it so it doesn't linger.
    push_app("bgtrend", None)

    while True:
        now = time.monotonic()

        if now >= next_bg:
            readings = dexcom.readings()
            push_app("bg", render_bg(readings))
            check_alarm(readings, state)
            next_bg = now + BG_INTERVAL

        if now >= next_claude:
            usage = claude_usage()
            push_app(CLAUDE_APP, render_claude(usage))
            push_app(CLAUDE_WEEK_APP, render_claude_week(usage))
            next_claude = now + CLAUDE_INTERVAL

        if once:
            return

        time.sleep(5)


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="awtrix",
        description="Bridge Dexcom G7 glucose and Claude plan usage to an AWTRIX 3.",
    )
    ap.add_argument("--once", action="store_true", help="single pass then exit")
    ap.add_argument("--selftest", action="store_true", help="push dummy values")
    ap.add_argument("--install-icons", action="store_true",
                    help="upload icons/*.jpg to the device, then exit")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.install_icons:
        install_icons()
        return

    if args.selftest:
        selftest()
        return

    try:
        run(once=args.once)
    except KeyboardInterrupt:
        sys.exit(0)
