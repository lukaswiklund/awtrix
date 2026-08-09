"""Dexcom Share client, the bg app payload, and the urgent-low alarm."""

from __future__ import annotations

import time
from datetime import datetime

from pydexcom import Dexcom as PyDexcom

from .config import (
    ARROWS,
    BG_ICON,
    BG_ICONS,
    COLORS,
    DEXCOM_PASSWORD,
    DEXCOM_REGION,
    DEXCOM_USERNAME,
    HIGH,
    LOW,
    STALE_AFTER,
    UNITS,
    URGENT_HIGH,
    URGENT_LOW,
    log,
)
from .transport import indicator, notify


def bg_state(value: float) -> str:
    """Range name, used to pick both the colour and the icon."""
    if value < URGENT_LOW:
        return "urgent_low"
    if value < LOW:
        return "low"
    if value <= HIGH:
        return "in_range"
    if value <= URGENT_HIGH:
        return "high"
    return "urgent_high"


def age_seconds(dt: datetime) -> float:
    now = datetime.now(dt.tzinfo) if dt.tzinfo is not None else datetime.now()
    return (now - dt).total_seconds()


def reading_value(reading) -> float:
    return reading.mmol_l if UNITS == "mmol" else float(reading.value)


def fmt(value: float) -> str:
    return f"{value:.1f}" if UNITS == "mmol" else f"{value:.0f}"


class Dexcom:
    """Lazy, self-healing wrapper. Share sessions expire; rebuild on failure."""

    def __init__(self):
        self._client = None

    def _connect(self):
        if not DEXCOM_USERNAME or not DEXCOM_PASSWORD:
            raise RuntimeError(
                "DEXCOM_USERNAME/DEXCOM_PASSWORD are unset -- put them in .env "
                "(see .env.example)"
            )
        self._client = PyDexcom(
            username=DEXCOM_USERNAME,
            password=DEXCOM_PASSWORD,
            region=DEXCOM_REGION,
        )
        log.info("dexcom session established (region=%s)", DEXCOM_REGION)

    def readings(self, minutes=30, max_count=1):
        for attempt in (1, 2):
            try:
                if self._client is None:
                    self._connect()
                return self._client.get_glucose_readings(
                    minutes=minutes, max_count=max_count
                )
            except Exception as e:
                log.warning("dexcom fetch failed (attempt %d): %s", attempt, e)
                self._client = None
                if attempt == 2:
                    return None
                time.sleep(2)
        return None


def render_bg(readings) -> dict:
    """Return the bg app payload."""
    if not readings:
        return {
            "text": "BG?",
            "color": COLORS["error"],
            "icon": BG_ICON or BG_ICONS["stale"],
            "textCase": 2,
            "lifetime": 1800,
            "lifetimeMode": 1,
        }

    latest = readings[0]
    value = reading_value(latest)
    age = age_seconds(latest.datetime)
    stale = age > STALE_AFTER

    arrow = ARROWS.get(latest.trend_direction, "")
    state = "stale" if stale else bg_state(value)
    colour = COLORS[state]

    text = [{"t": fmt(value), "c": colour.lstrip("#")}]
    if arrow and not stale:
        text.append({"t": arrow, "c": colour.lstrip("#")})
    if stale:
        text.append({"t": f" {int(age // 60)}m", "c": "606060"})

    return {
        "text": text,
        "icon": BG_ICON or BG_ICONS[state],
        "textCase": 2,
        "center": True,
        "noScroll": False,
        # If the bridge dies, mark the app staled rather than showing a lie.
        "lifetime": STALE_AFTER,
        "lifetimeMode": 1,
    }


def check_alarm(readings, state: dict) -> None:
    """One-shot notification on urgent low. Not a substitute for Dexcom alarms."""
    if not readings:
        return
    latest = readings[0]
    value = reading_value(latest)
    if age_seconds(latest.datetime) > STALE_AFTER:
        return

    urgent = value < URGENT_LOW
    if urgent and not state.get("alarmed"):
        notify(
            {
                "text": f"LOW {fmt(value)}",
                "color": COLORS["urgent_low"],
                "textCase": 2,
                "duration": 20,
                "wakeup": True,
                "blinkText": 500,
            }
        )
        indicator(1, {"color": COLORS["urgent_low"], "blink": 500})
        state["alarmed"] = True
    elif not urgent and state.get("alarmed"):
        indicator(1, {"color": "0"})
        state["alarmed"] = False
