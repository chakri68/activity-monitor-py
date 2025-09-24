from __future__ import annotations

"""Gemini API key storage & retrieval.

Strategy:
 - Try OS keyring via 'keyring' package.
 - Fallback to simple XOR-obfuscated file (NOT strong encryption, but avoids plain text) to meet MVP privacy requirement.
 - Redaction helper for logs.
"""

import base64
import logging
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - environment dependent
    import keyring  # type: ignore
except Exception:  # pragma: no cover
    keyring = None  # type: ignore

SERVICE_NAME = "activity_planner_gemini"
FALLBACK_FILENAME = "gemini.key"
_log = logging.getLogger(__name__)


def save_api_key(base_dir: Path, api_key: str) -> None:
    if keyring:
        try:
            keyring.set_password(SERVICE_NAME, "default", api_key)
            _log.info("api key stored in keyring")
            return
        except Exception:
            _log.warning("keyring storage failed; falling back to file")
    # Fallback: weak obfuscation
    encoded = _xor_obfuscate(api_key.encode("utf-8"))
    path = base_dir / FALLBACK_FILENAME
    path.write_bytes(encoded)
    _log.info("api key stored in fallback file", extra={"_json_location": "fallback"})


def load_api_key(base_dir: Path) -> Optional[str]:
    if keyring:
        try:
            v = keyring.get_password(SERVICE_NAME, "default")
            if v:
                return v
        except Exception:
            pass
    path = base_dir / FALLBACK_FILENAME
    if path.exists():
        try:
            raw = path.read_bytes()
            return _xor_deobfuscate(raw).decode("utf-8")
        except Exception:
            return None
    return None


def redact(value: str | None) -> str:
    if not value:
        return "<none>"
    if len(value) <= 6:
        return "***"
    return value[:3] + "***" + value[-3:]


def _xor_obfuscate(data: bytes) -> bytes:
    key = b"activity-planner-xor"
    return base64.b64encode(bytes([b ^ key[i % len(key)] for i, b in enumerate(data)]))


def _xor_deobfuscate(data: bytes) -> bytes:
    raw = base64.b64decode(data)
    key = b"activity-planner-xor"
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(raw)])


__all__ = ["save_api_key", "load_api_key", "redact"]
