from __future__ import annotations

"""Gemini API client and title categorization pipeline.

This provides a thin wrapper with retries + backoff and a categorizer that
maps window titles to existing activity names using the model, with a fallback
"Other" if confidence is below threshold or an error occurs.

Network calls are kept minimal; tests mock HTTP transport.
"""

from dataclasses import dataclass
import os
import json
import time
from typing import Iterable, Optional
import logging
import httpx

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


class GeminiError(Exception):
    pass


@dataclass(slots=True)
class GeminiClientConfig:
    api_key: str
    timeout: float = 10.0
    max_retries: int = 3
    backoff_base: float = 0.75


class GeminiClient:
    def __init__(self, config: GeminiClientConfig, transport: httpx.BaseTransport | None = None):
        self._config = config
        self._client = httpx.Client(timeout=config.timeout, transport=transport)

    def close(self):  # pragma: no cover simple
        self._client.close()

    # Public API ---------------------------------------------------------
    def classify_title(self, title: str, candidate_categories: Iterable[str]) -> dict:
        """Return {category, confidence} or raise GeminiError.

        Prompts Gemini to output JSON: {"category": str, "confidence": 0-1}.
        """
        categories_str = ", ".join(candidate_categories)
        prompt = (
            "Classify the following window title into one of the categories: "
            f"[{categories_str}]. If none fit, respond with Other."
            "Return JSON with keys 'category' and 'confidence' (0-1)."
            f" Title: '{title}'."
        )
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        api_key = self._config.api_key
        if not api_key:
            raise GeminiError("API key missing")
        params = {"key": api_key}
        attempt = 0
        while True:
            try:
                resp = self._client.post(GEMINI_ENDPOINT, params=params, json=body)
                if resp.status_code == 429:
                    raise GeminiError("rate_limited")
                if resp.status_code >= 400:
                    raise GeminiError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                text_blocks = []
                for c in data.get("candidates", []):
                    for part in c.get("content", {}).get("parts", []):
                        t = part.get("text")
                        if t:
                            text_blocks.append(t)
                joined = "\n".join(text_blocks)
                # Try parse JSON within text
                category = "Other"
                confidence = 0.0
                try:
                    # Extract first JSON object in output
                    start = joined.find("{")
                    end = joined.rfind("}")
                    if start != -1 and end != -1:
                        obj = json.loads(joined[start : end + 1])
                        category = str(obj.get("category", "Other"))
                        confidence = float(obj.get("confidence", 0.0))
                except Exception as parse_err:  # pragma: no cover - defensive
                    logger.warning("Parse error in Gemini response: %s", parse_err)
                return {"category": category, "confidence": confidence, "raw": joined}
            except GeminiError as e:
                attempt += 1
                if attempt > self._config.max_retries:
                    raise
                # backoff
                sleep_for = self._config.backoff_base * (2 ** (attempt - 1))
                time.sleep(sleep_for)
            except Exception as e:  # network or JSON
                attempt += 1
                if attempt > self._config.max_retries:
                    raise GeminiError(str(e))
                time.sleep(self._config.backoff_base * (2 ** (attempt - 1)))


# Categorization Service -----------------------------------------------------
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class TitleCategorizer(QObject):
    suggestion_ready = pyqtSignal(str, float, str)  # category, confidence, original_title
    error = pyqtSignal(str)

    def __init__(self, db, activity_store, client: GeminiClient | None, confidence_threshold: float = 0.55):
        super().__init__()
        self._db = db
        self._store = activity_store
        self._client = client
        self._threshold = confidence_threshold
        self._queue: list[str] = []
        self._processing = False
        self._timer = QTimer(self)
        self._timer.setInterval(200)  # slight delay to coalesce rapid changes
        self._timer.timeout.connect(self._process_next)
        self._timer.start()

    def submit_title(self, title: str):
        if not title or any(len(title) < 2 for title in [title]):  # trivial filter
            return
        if title in self._queue:
            return
        self._queue.append(title)

    def _process_next(self):  # pragma: no cover timing-based
        if self._processing or not self._queue:
            return
        title = self._queue.pop(0)
        self._processing = True
        try:
            # Rules first
            from .repositories import find_rule_for_title

            rule_activity = find_rule_for_title(self._db, title)
            if rule_activity:
                self.suggestion_ready.emit(rule_activity.title, 1.0, title)
                return
            if not self._client:
                return
            acts = [a.title for a in self._store.activities()]
            try:
                result = self._client.classify_title(title, acts + ["Other"])
            except GeminiError as e:
                self.error.emit(str(e))
                return
            cat = result.get("category", "Other")
            conf = float(result.get("confidence", 0.0))
            if conf >= self._threshold and cat in acts:
                self.suggestion_ready.emit(cat, conf, title)
        finally:
            self._processing = False


__all__ = [
    "GeminiClient",
    "GeminiClientConfig",
    "GeminiError",
    "TitleCategorizer",
]
