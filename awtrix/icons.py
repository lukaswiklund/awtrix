"""Upload the bg droplet icons to the device's /ICONS."""

from __future__ import annotations

import requests

from .config import AWTRIX_IP, ICONS_DIR, log


def install_icons() -> None:
    """Upload icons/*.jpg to the device's /ICONS. Re-run after a reflash."""
    if not AWTRIX_IP:
        log.error("AWTRIX_IP is unset -- set it in .env before installing icons")
        return

    try:
        names = sorted(p for p in ICONS_DIR.iterdir() if p.suffix == ".jpg")
    except OSError as e:
        log.error("cannot read %s: %s", ICONS_DIR, e)
        return

    for path in names:
        with path.open("rb") as f:
            # The file manager takes the destination path as the upload filename.
            files = {"data": (f"/ICONS/{path.name}", f, "image/jpeg")}
            try:
                r = requests.post(f"http://{AWTRIX_IP}/edit", files=files, timeout=20)
                r.raise_for_status()
                log.info("uploaded %s", path.name)
            except requests.RequestException as e:
                log.error("upload of %s failed: %s", path.name, e)
