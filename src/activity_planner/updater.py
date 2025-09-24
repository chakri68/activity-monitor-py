from __future__ import annotations

"""Basic GitHub release checker (Phase 10 auto-update notification)."""

import json
import logging
import threading
from dataclasses import dataclass
from typing import Optional, Callable
from urllib.request import urlopen
from packaging import version as _v

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class UpdateInfo:
    current: str
    latest: str
    download_url: str | None


def check_for_update_async(repo: str, current_version: str, callback: Callable[[Optional[UpdateInfo]], None]):  # pragma: no cover network
    def worker():
        try:
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            with urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "")
            assets = data.get("assets", [])
            dl_url = None
            if assets:
                # pick first asset
                dl_url = assets[0].get("browser_download_url")
            if tag and _v.parse(tag.strip("v")) > _v.parse(current_version):
                callback(UpdateInfo(current=current_version, latest=tag.strip("v"), download_url=dl_url))
            else:
                callback(None)
        except Exception as e:
            _log.warning("update check failed: %s", e)
            callback(None)

    threading.Thread(target=worker, daemon=True).start()


__all__ = ["check_for_update_async", "UpdateInfo"]
