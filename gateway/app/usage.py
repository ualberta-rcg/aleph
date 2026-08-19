"""Usage / accounting logger for the model gateway.

Writes one JSON object per served request to a dedicated, app-log-separate file
inside the gateway pod (default /var/log/aleph/usage.log, rotated). This is the
source feed for fairshare / billing: it captures *who* (identity), *what* (model,
api, endpoint), *how much* (full token breakdown incl. reasoning/cached detail
verbatim from vLLM), *on what* (gpu product, gpu count, vram, cpu, ram, node),
and *how long* (latency, derived gpu_seconds), plus whether the call triggered a
cold start (scale-from-zero) — which carries real GPU cost of its own.

The file stays on the RWX usage-log PVC (per-pod subdirectory). Ship it to a
central log/metrics system out of band later; if the file handler cannot be
created the logger degrades to stdout so accounting events are never silently
dropped.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler

USAGE_LOG_PATH = os.environ.get("GATEWAY_USAGE_LOG", "/var/log/aleph/usage.log")
SITE_NAME = os.environ.get("SITE_NAME", "aleph")
_MAX_BYTES = int(os.environ.get("GATEWAY_USAGE_LOG_MAX_BYTES", str(50 * 1024 * 1024)))
_BACKUPS = int(os.environ.get("GATEWAY_USAGE_LOG_BACKUPS", "5"))

_logger = logging.getLogger("aleph.usage")
_logger.setLevel(logging.INFO)
_logger.propagate = False


def _init_handler() -> None:
    if _logger.handlers:
        return
    try:
        d = os.path.dirname(USAGE_LOG_PATH)
        if d:
            os.makedirs(d, exist_ok=True)
        h: logging.Handler = RotatingFileHandler(
            USAGE_LOG_PATH, maxBytes=_MAX_BYTES, backupCount=_BACKUPS
        )
    except Exception as e:  # pragma: no cover - fall back so we never drop events
        print(f"[USAGE] file handler init failed ({USAGE_LOG_PATH}): {e}; using stdout",
              flush=True)
        h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(h)


_init_handler()

# Per-model rollup counters exposed on /metrics (Prometheus scrape).
_COUNTERS_LOCK = threading.Lock()
# model -> {requests, errors, prompt_tokens, completion_tokens, total_tokens,
#           cold_starts, gpu_seconds}
COUNTERS: dict[str, dict] = {}


def _bump(model: str, status: int, prompt: int, completion: int,
          total: int, cold_start: bool, gpu_seconds: float) -> None:
    with _COUNTERS_LOCK:
        c = COUNTERS.setdefault(model or "unknown", {
            "requests": 0, "errors": 0, "prompt_tokens": 0,
            "completion_tokens": 0, "total_tokens": 0,
            "cold_starts": 0, "gpu_seconds": 0.0,
        })
        c["requests"] += 1
        if status >= 400:
            c["errors"] += 1
        c["prompt_tokens"] += prompt
        c["completion_tokens"] += completion
        c["total_tokens"] += total
        if cold_start:
            c["cold_starts"] += 1
        c["gpu_seconds"] += gpu_seconds


def snapshot() -> dict[str, dict]:
    with _COUNTERS_LOCK:
        return {k: dict(v) for k, v in COUNTERS.items()}


def _i(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def record(
    *,
    identity: str,
    identity_type: str,
    account: str | None,
    endpoint: str,
    api: str,
    model: str,
    status: int,
    latency_ms: int,
    usage: dict | None = None,
    resources: dict | None = None,
    context_window: int = 0,
    max_completion_tokens: int = 0,
    cold_start: bool = False,
    stream: bool = False,
    request_id: str | None = None,
    key_fp: dict | None = None,
) -> None:
    """Emit one accounting record. Never raises."""
    try:
        usage = usage or {}
        resources = resources or {}
        prompt = _i(usage.get("prompt_tokens"))
        completion = _i(usage.get("completion_tokens"))
        total = _i(usage.get("total_tokens")) or (prompt + completion)
        gpus = _i(resources.get("gpus"))
        gpu_seconds = round(gpus * (latency_ms / 1000.0), 4) if gpus else 0.0

        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
            "site": SITE_NAME,
            "identity": identity,
            "identity_type": identity_type,
            "account": account or identity,
            "endpoint": endpoint,
            "api": api,
            "model": model,
            "status": status,
            "stream": stream,
            "cold_start": cold_start,
            "latency_ms": latency_ms,
            "tokens": {
                # Normalized top-line totals for easy aggregation.
                "prompt": prompt,
                "completion": completion,
                "total": total,
                # Full upstream breakdown verbatim (reasoning/cached/audio detail
                # appears here when vLLM emits it — prompt_tokens_details,
                # completion_tokens_details.reasoning_tokens, etc.).
                "detail": usage,
            },
            "context_window": context_window,
            "max_completion_tokens": max_completion_tokens,
            "resources": resources,
            "derived": {"gpu_seconds": gpu_seconds},
        }
        if request_id:
            rec["request_id"] = request_id
        if key_fp:
            rec["key_fp"] = key_fp
        _logger.info(json.dumps(rec, separators=(",", ":"), ensure_ascii=False))
        _bump(model, status, prompt, completion, total, cold_start, gpu_seconds)
    except Exception as e:  # pragma: no cover
        print(f"[USAGE] record failed: {e}", flush=True)
