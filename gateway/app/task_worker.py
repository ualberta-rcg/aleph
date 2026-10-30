"""Aleph Task Worker entrypoint (`uvicorn task_worker:app --host 0.0.0.0 --port 8080`).

Runs on worker nodes (`node-role.kubernetes.io/worker: "true"`) with the RWX
`/tasks` PVC (`aleph-tasks`) mounted locally. Shares the gateway's Kubernetes
watches (`CARDS`, `ISVC_STATE`, `POD_PHASE`, `NODE_LABELS`) and capacity-aware
predictor wake logic while executing queued `/v1/tasks` sequentially 1-by-1.
"""
from __future__ import annotations

import os

os.environ.setdefault("TASK_WORKER_LOCAL", "1")
os.environ.setdefault("TASK_STORAGE_MODE", "local")

try:
    from gateway import app  # type: ignore # noqa: E402,F401
except ImportError:
    from .gateway import app  # noqa: E402,F401
