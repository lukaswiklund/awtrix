"""AWTRIX 3 bridge: Dexcom G7 glucose + Claude usage.

Pushes two custom apps to an AWTRIX 3 device (Ulanzi TC001):
  bg      - current glucose + trend arrow, colour-coded, droplet icon
  claude  - Claude plan usage: percent used and time to reset

NOT A MEDICAL DEVICE. Dexcom Share is an undocumented API, readings lag the
sensor by several minutes, and this bridge can silently stall. Do not make
treatment decisions from the clock. Keep the real Dexcom app as your alarm.
"""

__all__ = ["claude", "config", "dexcom", "icons", "transport"]
