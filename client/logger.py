from __future__ import annotations

import logging
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

LOG_PATH = os.path.join(os.path.dirname(__file__), "request.log")

_logger: Optional[logging.Logger] = None


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    logger = logging.getLogger("request_logger")
    logger.setLevel(logging.INFO)
    # avoid adding multiple handlers if module is re-imported
    if not logger.handlers:
        # If the log file does not exist or is empty, write a start header
        try:
            need_header = not os.path.exists(LOG_PATH) or os.path.getsize(LOG_PATH) == 0
        except Exception:
            need_header = False
        if need_header:
            try:
                with open(LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat() + "Z", "event": "log_started"}, ensure_ascii=False) + "\n")
            except Exception:
                # best-effort: ignore header write failures
                pass

        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fmt = logging.Formatter("%(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    _logger = logger
    return _logger


def _sanitize(obj: Any) -> Any:
    """Recursively sanitize a params-like dict/list by masking secrets."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            lk = k.lower()
            if any(s in lk for s in ("secret", "token", "authorization", "password")):
                out[k] = "***"
            else:
                out[k] = _sanitize(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_sanitize(x) for x in obj]
    return obj


def log_api_call(url: str, params: Optional[Dict[str, Any]] = None, success: bool = True, message: Optional[str] = None, elapsed_ms: Optional[int] = None) -> None:
    """Write a structured one-line JSON log entry to request.log.

    Fields: timestamp, url, params (sanitized), success (bool), message
    """
    logger = _get_logger()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "url": url,
        "params": _sanitize(params or {}),
        "success": bool(success),
    "message": message,
    "elapsed_ms": elapsed_ms,
    }
    # one JSON object per line
    logger.info(json.dumps(entry, ensure_ascii=False))


__all__ = ["log_api_call"]
