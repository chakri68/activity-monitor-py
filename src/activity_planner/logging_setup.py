from __future__ import annotations

"""Central logging configuration with rotating files & structured output."""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

LOG_DIR_NAME = "logs"
LOG_FILE_BASENAME = "app.log"


class JsonFormatter(logging.Formatter):  # pragma: no cover
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: Dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Extra fields
        for k, v in record.__dict__.items():
            if k.startswith("_json_"):
                payload[k[6:]] = v
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(base_dir: Path, level: int = logging.INFO) -> Path:  # pragma: no cover
    log_dir = base_dir / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir / LOG_FILE_BASENAME
    root = logging.getLogger()
    root.setLevel(level)
    # Clear existing handlers (avoid duplicate on hot reload)
    root.handlers.clear()
    handler = RotatingFileHandler(logfile, maxBytes=512_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    # Also console minimal
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(ch)
    logging.getLogger(__name__).info("logging initialised", extra={"_json_phase": "startup"})
    return logfile


__all__ = ["configure_logging"]
