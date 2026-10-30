"""
Asynchronous Task System (/v1/tasks) for the Aleph inference gateway.

Leverages the existing model card ConfigMap fields (`input_map`,
`custom_params.schema`, `custom_params.passthrough`, `output_map`,
`defaults.chat`, `endpoints`, `routing`, `limits`, `scaling`) and gateway
pipeline (`prepare_chat`, `forward_custom`, `_can_schedule`, `_wake_up`,
`usage.record`).

Supports two execution modes:
- Local storage mode (`TASKS_DIR` mounted or `TASK_STORAGE_MODE=local` /
  `TASK_WORKER_LOCAL=1`, as inside `aleph-task-worker` on worker nodes or in
  unit/canary tests): stages files under `<TASKS_DIR>/<key_hash>/<task_id>/`
  and runs the 1-by-1 sequential worker loop.
- Zero-mount proxy mode (default inside control-plane `model-gateway` pods
  when `/tasks` is not mounted so `63-model-gateway.yaml` stays untouched):
  serves catalog/introspection directly and proxies `/v1/tasks` file/state
  requests to `Service/aleph-task-worker` (`TASK_WORKER_URL`).
"""
from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import io
import json
import logging
import os
import re
import shutil
import smtplib
import tarfile
import time
import traceback
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response

log = logging.getLogger("aleph.tasks")

DEFAULT_TASKS_DIR = "/tasks"
DEFAULT_REDIS_URL = ""
DEFAULT_TASK_WORKER_URL = "http://aleph-task-worker.models.svc.cluster.local"

ENVELOPE_KEY_SET = frozenset(
    {
        "model",
        "files",
        "file",
        "inputs",
        "params",
        "file_params",
        "notify_email",
        "loop_mode",
        "file_grouping",
        "unpack_archive",
        "continue_on_item_error",
        "endpoint",
    }
)

ACTIVE_TASK_STATUSES = frozenset({"queued", "waking_pod", "running"})
TERMINAL_TASK_STATUSES = frozenset({"completed", "failed", "cancelled", "expired"})

# Minimal valid 1x1 white PNG for synthetic/fallback PDF page rendering
_FALLBACK_1X1_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:16]}"


def _safe_filename(name: str, default: str = "file.bin") -> str:
    base = os.path.basename(str(name or "").replace("\\", "/")).strip()
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base[:180] if base else default


# ---------------------------------------------------------------------------
# Card mode & property introspection (reuses details.yaml fields directly)
# ---------------------------------------------------------------------------
def card_mode(card: dict | None) -> str:
    """Return effective model mode: 'api' | 'task' | 'both'."""
    if not isinstance(card, dict):
        return "api"
    explicit = str(card.get("mode") or "").strip().lower()
    if explicit in ("api", "task", "both"):
        return explicit
    tasks_cfg = card.get("tasks")
    if isinstance(tasks_cfg, dict):
        tmode = str(tasks_cfg.get("mode") or "").strip().lower()
        if tmode in ("api", "task", "both"):
            return tmode
        if tasks_cfg.get("enabled") is True:
            ep = str((card.get("endpoints") or {}).get("primary") or "").strip()
            if card.get("type") == "ocr" or ep == "/v1/tasks":
                return "task"
            return "both"
    return "api"


def _normalize_prop_spec(name: str, spec: Any) -> dict[str, Any]:
    """Normalize an `input_map` or `custom_params.schema` entry into a property dict."""
    if isinstance(spec, dict):
        if "type" in spec or "description" in spec or "default" in spec or "required" in spec:
            out = dict(spec)
            out.setdefault("type", "string")
            out.setdefault("required", False)
            return out
        return {
            "type": "object",
            "required": False,
            "fields": spec,
            "description": f"Nested object map for '{name}'",
        }
    return {
        "type": "string",
        "required": False,
        "description": str(spec),
    }


def extract_card_defaults(card: dict) -> dict[str, Any]:
    """Seed parameter defaults from the card's existing sections:
    `defaults.chat`, `input_map.*.default`, `custom_params.schema.*.default`,
    and optional `tasks.default_params`."""
    merged: dict[str, Any] = {}
    chat_defaults = ((card.get("defaults") or {}).get("chat") or {})
    if isinstance(chat_defaults, dict):
        for k, v in chat_defaults.items():
            if k != "thinking" and v is not None:
                merged[k] = v
    imap = card.get("input_map") or {}
    if isinstance(imap, dict):
        for k, v in imap.items():
            if isinstance(v, dict) and v.get("default") is not None:
                merged.setdefault(k, v["default"])
    cschema = ((card.get("custom_params") or {}).get("schema") or {})
    if isinstance(cschema, dict):
        for k, v in cschema.items():
            if isinstance(v, dict) and v.get("default") is not None:
                merged.setdefault(k, v["default"])
    tdefaults = ((card.get("tasks") or {}).get("default_params") or {})
    if isinstance(tdefaults, dict):
        merged.update(tdefaults)
    return merged


def extract_card_properties(card: dict) -> dict[str, dict[str, Any]]:
    """Build unified parameter properties dict from the card's existing
    `input_map`, `custom_params.schema`, and optional `tasks.properties`."""
    props: dict[str, dict[str, Any]] = {}
    imap = card.get("input_map") or {}
    if isinstance(imap, dict):
        for k, v in imap.items():
            if k == "model":
                continue
            props[k] = _normalize_prop_spec(k, v)
    cschema = ((card.get("custom_params") or {}).get("schema") or {})
    if isinstance(cschema, dict):
        for k, v in cschema.items():
            if k not in props:
                props[k] = _normalize_prop_spec(k, v)
            elif isinstance(v, dict):
                props[k].update(v)
    tprops = ((card.get("tasks") or {}).get("properties") or {})
    if isinstance(tprops, dict):
        for k, v in tprops.items():
            props[k] = _normalize_prop_spec(k, v)
    return props


ENVELOPE_PROPERTIES: dict[str, dict[str, Any]] = {
    "model": {
        "type": "string",
        "required": True,
        "description": "Public model ID (e.g. 'glm-ocr', 'kandinsky-3', 'aurora').",
    },
    "files": {
        "type": "file[]",
        "required": False,
        "description": "1..N uploaded input files (multipart/form-data `-F files=@...` or `-F file=@...`). Processed sequentially 1-by-1 on the warm predictor pod.",
    },
    "inputs": {
        "type": "array",
        "required": False,
        "description": "Ordered array of per-item input objects when submitting via application/json.",
    },
    "params": {
        "type": "object",
        "required": False,
        "description": "Task-wide model parameters merged onto every item (can also be passed as flat `-F <key>=<value>` form fields). Unlisted model parameters are passed straight through.",
    },
    "file_params": {
        "type": "object",
        "required": False,
        "description": "Per-file parameter overrides keyed by filename or 0-based index (e.g. `{\"paper2.pdf\": {\"dpi\": 300, \"pages\": \"1-5\"}}`).",
    },
    "loop_mode": {
        "type": "string",
        "required": False,
        "enum": ["pdf_pages", "items", "rollout_steps"],
        "description": "Sequential execution loop mode (defaults to the model card's `tasks.loop_mode`).",
    },
    "file_grouping": {
        "type": "string",
        "required": False,
        "default": "per_file",
        "enum": ["per_file", "bundle"],
        "description": "'per_file' sends each file 1-by-1; 'bundle' groups uploaded images into an array for multi-image models (e.g. qwen-image-2-1, dust3r).",
    },
    "unpack_archive": {
        "type": "boolean",
        "required": False,
        "default": False,
        "description": "When true, uploaded .zip / .tar.gz archives are unpacked into ordered task items.",
    },
    "continue_on_item_error": {
        "type": "boolean",
        "required": False,
        "default": True,
        "description": "When true (default), an error on item i is logged to error.log and the worker continues with item i+1.",
    },
    "endpoint": {
        "type": "string",
        "required": False,
        "description": "Optional endpoint selector ('primary' or 'edit' for dual-endpoint image models; auto-selected when image files are uploaded).",
    },
    "notify_email": {
        "type": "string",
        "required": False,
        "description": "Strictly opt-in email address to notify when the task finishes. Never sent unless explicitly provided.",
    },
}


def build_task_info(
    card: dict,
    isvc_state: dict | None = None,
    pods: dict | None = None,
    host_url: str = "https://inference.vulcan.alliancecan.ca",
) -> dict[str, Any]:
    """Synthesize self-describing task metadata & properties from a model card."""
    mode = card_mode(card)
    enabled = mode in ("task", "both")
    tasks_cfg = (card.get("tasks") or {}) if isinstance(card.get("tasks"), dict) else {}
    mtype = str(card.get("type") or "chat").lower()
    endpoints = (card.get("endpoints") or {}) if isinstance(card.get("endpoints"), dict) else {}
    routing = (card.get("routing") or {}) if isinstance(card.get("routing"), dict) else {}

    if tasks_cfg.get("loop_mode"):
        loop_mode = str(tasks_cfg["loop_mode"])
    elif mtype == "ocr":
        loop_mode = "pdf_pages"
    elif mtype == "forecast":
        loop_mode = "rollout_steps"
    else:
        loop_mode = "items"

    file_grouping = str(tasks_cfg.get("file_grouping") or "per_file")
    if tasks_cfg.get("unit"):
        unit = str(tasks_cfg["unit"])
    elif loop_mode == "pdf_pages":
        unit = "pages"
    elif loop_mode == "rollout_steps":
        unit = "steps"
    elif mtype == "image":
        unit = "images"
    else:
        unit = "files"

    default_unit_seconds = float(tasks_cfg.get("default_unit_seconds") or (3.5 if loop_mode == "pdf_pages" else 5.0))
    yield_to_sync_seconds = float(
        tasks_cfg.get("yield_to_sync_seconds", 2.0 if mode == "both" else 0.0)
    )
    retention_hours = int(tasks_cfg.get("retention_hours") or 24)

    if tasks_cfg.get("accepted_inputs"):
        accepted_inputs = list(tasks_cfg["accepted_inputs"])
    elif loop_mode == "pdf_pages" or mtype == "ocr":
        accepted_inputs = [".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp", ".zip", ".tar.gz"]
    elif mtype == "image":
        accepted_inputs = [".png", ".jpg", ".jpeg", ".webp", ".txt", ".jsonl", ".zip", ".tar.gz"]
    else:
        accepted_inputs = [".json", ".jsonl", ".txt", ".csv", ".npy", ".npz", ".pdb", ".sdf", ".nii.gz", ".zip", ".tar.gz"]

    if tasks_cfg.get("output_formats"):
        output_formats = list(tasks_cfg["output_formats"])
    elif loop_mode == "pdf_pages" or mtype == "ocr":
        output_formats = [".md", ".json", ".txt", ".zip"]
    elif mtype == "image":
        output_formats = [".png", ".meta.json", ".zip"]
    else:
        output_formats = [".json", ".txt", ".zip"]

    default_params = extract_card_defaults(card)
    properties = extract_card_properties(card)
    passthrough = bool(((card.get("custom_params") or {}).get("passthrough")))

    tlimits = (tasks_cfg.get("limits") or {}) if isinstance(tasks_cfg.get("limits"), dict) else {}
    limits = {
        "max_files_per_task": int(tlimits.get("max_files_per_task") or os.environ.get("TASK_MAX_FILES", "200")),
        "max_upload_mb": int(tlimits.get("max_upload_mb") or os.environ.get("TASK_MAX_UPLOAD_MB", "512")),
        "max_pages_per_pdf": int(tlimits.get("max_pages_per_pdf") or os.environ.get("TASK_MAX_PAGES_PER_PDF", "500")),
        "max_active_tasks_per_user": int(tlimits.get("max_active_tasks_per_user") or os.environ.get("TASK_MAX_ACTIVE_PER_USER", "10")),
        "timeout_seconds": int(tlimits.get("timeout_seconds") or 3600),
    }

    mid = card.get("id", "model")
    upstream_primary = routing.get("upstream_path") or endpoints.get("primary") or "/v1/chat/completions"
    if upstream_primary == "/v1/tasks":
        upstream_primary = routing.get("upstream_path") or "/v1/chat/completions"

    if loop_mode == "pdf_pages" or mtype == "ocr":
        curl_submit_mp = (
            f'curl -sS -X POST {host_url}/v1/tasks \\\n'
            f'  -H "Authorization: Bearer $KEY" \\\n'
            f'  -F model={mid} \\\n'
            f'  -F "files=@document1.pdf" \\\n'
            f'  -F "files=@document2.pdf" \\\n'
            f'  -F "dpi=200" \\\n'
            f'  -F "prompt=Text Recognition:"'
        )
        curl_submit_json = (
            f'curl -sS -X POST {host_url}/v1/tasks \\\n'
            f'  -H "Authorization: Bearer $KEY" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f'  -d \'{{"model":"{mid}","params":{{"prompt":"Text Recognition:"}},'
            f'"inputs":[{{"name":"page1.png","image_base64":"<base64>"}}]}}\''
        )
    elif mtype == "image":
        curl_submit_mp = (
            f'curl -sS -X POST {host_url}/v1/tasks \\\n'
            f'  -H "Authorization: Bearer $KEY" \\\n'
            f'  -F model={mid} \\\n'
            f'  -F "files=@input.png" \\\n'
            f'  -F "prompt=Oil painting in autumn colors" \\\n'
            f'  -F "strength=0.75"'
        )
        curl_submit_json = (
            f'curl -sS -X POST {host_url}/v1/tasks \\\n'
            f'  -H "Authorization: Bearer $KEY" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f'  -d \'{{"model":"{mid}","params":{{"num_inference_steps":25,"seed":42}},'
            f'"inputs":[{{"prompt":"A snowy forest under aurora"}},{{"prompt":"A mountain lake at sunrise"}}]}}\''
        )
    else:
        curl_submit_mp = (
            f'curl -sS -X POST {host_url}/v1/tasks \\\n'
            f'  -H "Authorization: Bearer $KEY" \\\n'
            f'  -F model={mid} \\\n'
            f'  -F "files=@input1.json" \\\n'
            f'  -F "files=@input2.json"'
        )
        curl_submit_json = (
            f'curl -sS -X POST {host_url}/v1/tasks \\\n'
            f'  -H "Authorization: Bearer $KEY" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f'  -d \'{{"model":"{mid}","params":{{}},"inputs":[{{}}]}}\''
        )

    examples = {
        "curl_submit_multipart": curl_submit_mp,
        "curl_submit_json": curl_submit_json,
        "curl_poll": f'curl -sS {host_url}/v1/tasks/$TASK_ID -H "Authorization: Bearer $KEY"',
        "curl_error_log": f'curl -sS {host_url}/v1/tasks/$TASK_ID/error.log -H "Authorization: Bearer $KEY"',
        "curl_result": f'curl -sS -L {host_url}/v1/tasks/$TASK_ID/result -H "Authorization: Bearer $KEY" -o $TASK_ID.zip',
    }

    return {
        "enabled": enabled,
        "mode": mode,
        "loop_mode": loop_mode,
        "file_grouping": file_grouping,
        "unit": unit,
        "default_unit_seconds": default_unit_seconds,
        "yield_to_sync_seconds": yield_to_sync_seconds,
        "retention_hours": retention_hours,
        "accepted_inputs": accepted_inputs,
        "output_formats": output_formats,
        "allows_unlisted_params": True,
        "passthrough": passthrough,
        "default_params": default_params,
        "properties": properties,
        "output_map": card.get("output_map", {}) or {},
        "envelope_properties": ENVELOPE_PROPERTIES,
        "limits": limits,
        "endpoints": {
            "submit": "/v1/tasks",
            "list": "/v1/tasks",
            "status": "/v1/tasks/{task_id}",
            "error_log": "/v1/tasks/{task_id}/error.log",
            "result": "/v1/tasks/{task_id}/result",
            "file": "/v1/tasks/{task_id}/files/out/{filename}",
            "cancel": "/v1/tasks/{task_id}",
            "upstream_primary": upstream_primary,
            "upstream_edit": endpoints.get("edit", ""),
        },
        "examples": examples,
    }


# ---------------------------------------------------------------------------
# Card-driven payload preparation (reuses gateway prepare_chat & forward_custom)
# ---------------------------------------------------------------------------
def prepare_chat_payload(
    body: dict[str, Any],
    card: dict[str, Any],
    prepare_chat_fn: Callable[[dict, dict], tuple[dict, bool]] | None = None,
) -> dict[str, Any]:
    """Prepare a chat/OCR/vLLM payload using the gateway's prepare_chat pipeline
    (applying defaults.chat, system_prompt, max_completion_tokens cap, and
    routing.upstream_model_id while preserving all custom/unlisted vLLM params).
    """
    out = copy.deepcopy(body)
    routing = (card.get("routing") or {}) if isinstance(card.get("routing"), dict) else {}
    info = {
        "id": card.get("id", out.get("model", "")),
        "card": card,
        "upstream_model_id": routing.get("upstream_model_id"),
    }
    if prepare_chat_fn is not None:
        prepared, _ = prepare_chat_fn(info, out)
    else:
        defaults = ((card.get("defaults") or {}).get("chat") or {})
        for k, v in defaults.items():
            if k in ("thinking", "system_prompt"):
                continue
            if k not in out or out[k] is None:
                out[k] = v
        cap = ((card.get("limits") or {}).get("max_completion_tokens"))
        if isinstance(cap, int) and cap > 0:
            mt = out.get("max_tokens")
            if not isinstance(mt, int) or mt > cap:
                out["max_tokens"] = cap
        if routing.get("upstream_model_id"):
            out["model"] = routing["upstream_model_id"]
        prepared = out

    # Inject default system_prompt from defaults.chat.system_prompt if declared and no system message present
    sys_prompt = ((card.get("defaults") or {}).get("chat") or {}).get("system_prompt")
    if sys_prompt and isinstance(prepared.get("messages"), list):
        has_sys = any(isinstance(m, dict) and m.get("role") in ("system", "developer") for m in prepared["messages"])
        if not has_sys:
            prepared["messages"] = [{"role": "system", "content": str(sys_prompt)}] + list(prepared["messages"])
    prepared["stream"] = False
    return prepared


def prepare_custom_payload(payload: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    """Prepare a payload for custom/image/science/audio/3D predictors using the
    card's `input_map`, `custom_params.schema`, `custom_params.passthrough`, and
    `routing.upstream_model_id`. Unlisted parameters are always preserved.
    """
    out = extract_card_defaults(card)
    out.update(copy.deepcopy(payload))

    props = extract_card_properties(card)
    # Convenient alias resolution (e.g. `steps` <-> `num_inference_steps`)
    if "steps" in out and "num_inference_steps" in props and "num_inference_steps" not in payload:
        out["num_inference_steps"] = out.pop("steps")
    elif "num_inference_steps" in out and "steps" in props and "steps" not in payload and "num_inference_steps" not in props:
        out["steps"] = out.pop("num_inference_steps")

    routing = (card.get("routing") or {}) if isinstance(card.get("routing"), dict) else {}
    custom_params = (card.get("custom_params") or {}) if isinstance(card.get("custom_params"), dict) else {}
    if custom_params.get("passthrough"):
        out.pop("model", None)
        out.pop("stream", None)
    elif routing.get("upstream_model_id") and "model" in out:
        out["model"] = routing["upstream_model_id"]
    return out


# ---------------------------------------------------------------------------
# Caller identity & key hashing
# ---------------------------------------------------------------------------
def extract_caller_identity(request: Request) -> tuple[str, str]:
    """Return (key_hash_16hex, owner_label) for per-API-key task isolation."""
    explicit_hash = (request.headers.get("x-tyk-key-hash") or "").strip()
    owner = (
        request.headers.get("x-aleph-identity")
        or request.headers.get("x-owner")
        or request.headers.get("x-tyk-owner")
        or "anonymous"
    ).strip()
    if explicit_hash and re.fullmatch(r"[0-9a-fA-F]{12,64}", explicit_hash):
        return explicit_hash[:16].lower(), owner

    auth = (request.headers.get("authorization") or "").strip()
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    elif auth:
        token = auth
    elif request.headers.get("x-api-key"):
        token = request.headers.get("x-api-key", "").strip()
    elif request.headers.get("api-key"):
        token = request.headers.get("api-key", "").strip()
    elif request.headers.get("x-goog-api-key"):
        token = request.headers.get("x-goog-api-key", "").strip()
    elif request.query_params.get("api_key"):
        token = request.query_params.get("api_key", "").strip()

    if not token:
        token = f"anon:{owner}"
    key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return key_hash, owner


# ---------------------------------------------------------------------------
# Minimal async RESP2 Redis client (stdlib only, optional fallback)
# ---------------------------------------------------------------------------
def _parse_redis_url(url: str) -> tuple[str, int]:
    u = url.strip()
    if u.startswith("redis://"):
        u = u[len("redis://"):]
    u = u.split("/", 1)[0]
    if "@" in u:
        u = u.split("@", 1)[1]
    if ":" in u:
        host, port_s = u.rsplit(":", 1)
        return host or "127.0.0.1", int(port_s)
    return u or "127.0.0.1", 6379


async def _redis_cmd(redis_url: str, *parts: str, timeout: float = 3.0) -> Any:
    host, port = _parse_redis_url(redis_url)
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    try:
        buf = [f"*{len(parts)}\r\n".encode("utf-8")]
        for p in parts:
            b = str(p).encode("utf-8")
            buf.append(f"${len(b)}\r\n".encode("utf-8") + b + b"\r\n")
        writer.write(b"".join(buf))
        await writer.drain()

        async def _read_resp() -> Any:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if not line:
                return None
            prefix = line[:1]
            payload = line[1:-2]
            if prefix == b"+":
                return payload.decode("utf-8", errors="replace")
            if prefix == b"-":
                raise RuntimeError(payload.decode("utf-8", errors="replace"))
            if prefix == b":":
                return int(payload)
            if prefix == b"$":
                ln = int(payload)
                if ln < 0:
                    return None
                data = await asyncio.wait_for(reader.readexactly(ln + 2), timeout=timeout)
                return data[:-2].decode("utf-8", errors="replace")
            if prefix == b"*":
                cnt = int(payload)
                if cnt < 0:
                    return None
                return [await _read_resp() for _ in range(cnt)]
            return None

        return await _read_resp()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# TaskStore: filesystem manifest + error.log + queue + 24h retention reaper
# ---------------------------------------------------------------------------
class TaskStore:
    def __init__(self, base_dir: str | Path | None = None, redis_url: str | None = None):
        self.base_dir = Path(base_dir or os.environ.get("TASKS_DIR", DEFAULT_TASKS_DIR))
        self.redis_url = (redis_url if redis_url is not None else os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)).strip()
        self._mem_queue: asyncio.Queue[str] = asyncio.Queue()
        self._queued_set: set[str] = set()
        self._lock = asyncio.Lock()

    def ensure_dirs(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "_index").mkdir(parents=True, exist_ok=True)

    def task_dir(self, key_hash: str, task_id: str) -> Path:
        return self.base_dir / key_hash / task_id

    def manifest_path(self, key_hash: str, task_id: str) -> Path:
        return self.task_dir(key_hash, task_id) / "manifest.json"

    def error_log_path(self, key_hash: str, task_id: str) -> Path:
        return self.task_dir(key_hash, task_id) / "error.log"

    def result_zip_path(self, key_hash: str, task_id: str) -> Path:
        return self.task_dir(key_hash, task_id) / "result.zip"

    def create_task(self, key_hash: str, manifest: dict[str, Any]) -> Path:
        self.ensure_dirs()
        tid = manifest["task_id"]
        tdir = self.task_dir(key_hash, tid)
        (tdir / "in").mkdir(parents=True, exist_ok=True)
        (tdir / "out").mkdir(parents=True, exist_ok=True)
        (tdir / "error.log").touch(exist_ok=True)
        self.save_manifest(key_hash, tid, manifest)
        idx_link = self.base_dir / "_index" / tid
        try:
            if idx_link.exists() or idx_link.is_symlink():
                idx_link.unlink()
            idx_link.symlink_to(tdir)
        except OSError:
            (self.base_dir / "_index" / f"{tid}.ref").write_text(f"{key_hash}/{tid}", encoding="utf-8")
        return tdir

    def save_manifest(self, key_hash: str, task_id: str, manifest: dict[str, Any]) -> None:
        tdir = self.task_dir(key_hash, task_id)
        tdir.mkdir(parents=True, exist_ok=True)
        mpath = tdir / "manifest.json"
        tmp = tdir / f".manifest.json.tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}"
        tmp.write_text(json.dumps(manifest, indent=2, sort_keys=False), encoding="utf-8")
        tmp.replace(mpath)

    def load_manifest(self, key_hash: str, task_id: str) -> dict[str, Any] | None:
        mpath = self.manifest_path(key_hash, task_id)
        if not mpath.is_file():
            return None
        try:
            return json.loads(mpath.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"Failed to load manifest {mpath}: {e}")
            return None

    def resolve_task(self, task_id: str) -> tuple[str, dict[str, Any]] | None:
        """Locate (key_hash, manifest) by task_id across the store."""
        idx = self.base_dir / "_index" / task_id
        if idx.is_dir():
            mpath = idx / "manifest.json"
            if mpath.is_file():
                try:
                    m = json.loads(mpath.read_text(encoding="utf-8"))
                    return str(m.get("key_hash") or idx.resolve().parent.name), m
                except Exception:
                    pass
        ref = self.base_dir / "_index" / f"{task_id}.ref"
        if ref.is_file():
            rel = ref.read_text(encoding="utf-8").strip()
            if "/" in rel:
                kh, tid = rel.split("/", 1)
                m = self.load_manifest(kh, tid)
                if m:
                    return kh, m
        if self.base_dir.is_dir():
            for kh_dir in self.base_dir.iterdir():
                if not kh_dir.is_dir() or kh_dir.name.startswith("_"):
                    continue
                m = self.load_manifest(kh_dir.name, task_id)
                if m:
                    return kh_dir.name, m
        return None

    def list_tasks(self, key_hash: str, status_filter: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        kh_dir = self.base_dir / key_hash
        if not kh_dir.is_dir():
            return []
        items: list[dict[str, Any]] = []
        for tdir in kh_dir.iterdir():
            if not tdir.is_dir():
                continue
            m = self.load_manifest(key_hash, tdir.name)
            if not m:
                continue
            if status_filter and m.get("status") != status_filter:
                continue
            items.append(self.public_manifest_view(m))
        items.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return items[: max(1, min(limit, 500))]

    def count_active_tasks(self, key_hash: str) -> int:
        kh_dir = self.base_dir / key_hash
        if not kh_dir.is_dir():
            return 0
        cnt = 0
        for tdir in kh_dir.iterdir():
            if not tdir.is_dir():
                continue
            m = self.load_manifest(key_hash, tdir.name)
            if m and m.get("status") in ACTIVE_TASK_STATUSES:
                cnt += 1
        return cnt

    def append_error_log(
        self,
        key_hash: str,
        task_id: str,
        *,
        item: str,
        stage: str,
        message: str,
        status_code: int | None = None,
        upstream_body: str | None = None,
        exc_tb: str | None = None,
    ) -> dict[str, Any]:
        ts = _iso_now()
        epath = self.error_log_path(key_hash, task_id)
        epath.parent.mkdir(parents=True, exist_ok=True)
        header = f"[{ts}] [ERROR] item={item}"
        if status_code is not None:
            header += f" status={status_code}"
        header += f" stage={stage}: {message}\n"
        lines = [header]
        if upstream_body:
            lines.append(f"  upstream_response: {upstream_body.strip()}\n")
        if exc_tb:
            for tb_line in exc_tb.strip().splitlines():
                lines.append(f"  {tb_line}\n")
        lines.append("\n")
        with epath.open("a", encoding="utf-8") as f:
            f.writelines(lines)
        return {
            "timestamp": ts,
            "item": item,
            "stage": stage,
            "status_code": status_code,
            "message": message,
        }

    def read_error_log(self, key_hash: str, task_id: str, tail_lines: int | None = None) -> str:
        epath = self.error_log_path(key_hash, task_id)
        if not epath.is_file():
            return ""
        text = epath.read_text(encoding="utf-8", errors="replace")
        if tail_lines and tail_lines > 0:
            all_lines = text.splitlines()
            return "\n".join(all_lines[-tail_lines:]) + ("\n" if all_lines else "")
        return text

    async def enqueue(self, key_hash: str, task_id: str) -> None:
        token = f"{key_hash}:{task_id}"
        if self.redis_url:
            try:
                await _redis_cmd(self.redis_url, "RPUSH", "aleph:tasks:queue", token)
                return
            except Exception as e:
                log.warning(f"Redis enqueue fallback to local memory queue ({e})")
        async with self._lock:
            if token not in self._queued_set:
                self._queued_set.add(token)
                await self._mem_queue.put(token)

    async def dequeue(self, timeout: float = 1.0) -> tuple[str, str] | None:
        if self.redis_url:
            try:
                res = await _redis_cmd(self.redis_url, "LPOP", "aleph:tasks:queue")
                if isinstance(res, str) and ":" in res:
                    kh, tid = res.split(":", 1)
                    return kh, tid
            except Exception:
                pass
        try:
            token = await asyncio.wait_for(self._mem_queue.get(), timeout=timeout)
            async with self._lock:
                self._queued_set.discard(token)
            if ":" in token:
                kh, tid = token.split(":", 1)
                return kh, tid
        except asyncio.TimeoutError:
            pass
        return None

    async def recover_pending_tasks(self) -> int:
        """Scan /tasks for queued/running tasks after worker restart and re-enqueue."""
        if not self.base_dir.is_dir():
            return 0
        recovered = 0
        candidates: list[tuple[str, str, str]] = []
        for kh_dir in self.base_dir.iterdir():
            if not kh_dir.is_dir() or kh_dir.name.startswith("_"):
                continue
            for tdir in kh_dir.iterdir():
                if not tdir.is_dir():
                    continue
                m = self.load_manifest(kh_dir.name, tdir.name)
                if not m:
                    continue
                if m.get("status") in ACTIVE_TASK_STATUSES:
                    candidates.append((str(m.get("created_at") or ""), kh_dir.name, tdir.name))
        candidates.sort(key=lambda x: x[0])
        for _, kh, tid in candidates:
            await self.enqueue(kh, tid)
            recovered += 1
        return recovered

    def reap_expired(self, now: datetime | None = None) -> list[str]:
        """Remove terminal tasks whose 24-hour post-completion retention has elapsed."""
        if not self.base_dir.is_dir():
            return []
        now_dt = now or _utc_now()
        reaped: list[str] = []
        for kh_dir in self.base_dir.iterdir():
            if not kh_dir.is_dir() or kh_dir.name.startswith("_"):
                continue
            for tdir in kh_dir.iterdir():
                if not tdir.is_dir():
                    continue
                m = self.load_manifest(kh_dir.name, tdir.name)
                if not m:
                    continue
                status = m.get("status")
                if status not in TERMINAL_TASK_STATUSES:
                    continue
                exp_str = m.get("expires_at")
                if not exp_str:
                    continue
                try:
                    exp_dt = datetime.fromisoformat(str(exp_str).replace("Z", "+00:00"))
                except Exception:
                    continue
                if now_dt >= exp_dt:
                    tid = m.get("task_id", tdir.name)
                    self.delete_task_files(kh_dir.name, tid)
                    reaped.append(tid)
        return reaped

    def delete_task_files(self, key_hash: str, task_id: str) -> bool:
        tdir = self.task_dir(key_hash, task_id)
        idx = self.base_dir / "_index" / task_id
        ref = self.base_dir / "_index" / f"{task_id}.ref"
        existed = tdir.exists()
        if tdir.exists():
            shutil.rmtree(tdir, ignore_errors=True)
        for p in (idx, ref):
            try:
                if p.exists() or p.is_symlink():
                    p.unlink()
            except OSError:
                pass
        return existed

    @staticmethod
    def public_manifest_view(m: dict[str, Any]) -> dict[str, Any]:
        """Return clean public task status dictionary without internal staging paths."""
        out = {k: v for k, v in m.items() if not k.startswith("_") and k != "key_hash"}
        tid = m.get("task_id", "")
        out.setdefault("error_count", len(m.get("errors") or []))
        out.setdefault("last_error", (m.get("errors") or [-1])[-1] if m.get("errors") else None)
        out.setdefault("error_log_url", f"/v1/tasks/{tid}/error.log")
        out.setdefault("result_url", f"/v1/tasks/{tid}/result")
        return out


# ---------------------------------------------------------------------------
# Safe archive unpacking, PDF rendering, & page-range parsing
# ---------------------------------------------------------------------------
def parse_page_range(spec: str | int | list[int] | None, total_pages: int) -> list[int]:
    """Parse 1-based page specification ('1-5,8,10-') into sorted 0-based page indices."""
    if total_pages <= 0:
        return []
    if spec is None or spec == "" or spec == "all":
        return list(range(total_pages))
    if isinstance(spec, int):
        return [spec - 1] if 1 <= spec <= total_pages else []
    if isinstance(spec, list):
        return sorted({int(p) - 1 for p in spec if 1 <= int(p) <= total_pages})
    pages: set[int] = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            s_str, e_str = part.split("-", 1)
            start = int(s_str) if s_str.strip() else 1
            end = int(e_str) if e_str.strip() else total_pages
            start = max(1, start)
            end = min(total_pages, end)
            for p in range(start, end + 1):
                pages.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                pages.add(p - 1)
    return sorted(pages)


def count_pdf_pages(pdf_path: Path) -> int:
    raw = pdf_path.read_bytes()
    if not raw.startswith(b"%PDF"):
        raise RuntimeError(f"File '{pdf_path.name}' is not a valid PDF header")
    try:
        import pypdfium2 as pdfium  # type: ignore
        doc = pdfium.PdfDocument(str(pdf_path))
        try:
            return len(doc)
        finally:
            doc.close()
    except ImportError:
        # Lightweight regex fallback for bare-host unit tests without pypdfium2
        matches = re.findall(rb"/Type\s*/Page\b", raw)
        if not matches:
            raise RuntimeError(f"Invalid or empty PDF '{pdf_path.name}'")
        return len(matches)
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF '{pdf_path.name}': {e}") from e


def render_pdf_page_png_b64(pdf_path: Path, page_idx_0based: int, dpi: int = 200) -> str:
    """Render a single PDF page to base64-encoded PNG."""
    raw = pdf_path.read_bytes()
    if not raw.startswith(b"%PDF"):
        raise RuntimeError(f"File '{pdf_path.name}' is not a valid PDF")
    try:
        import pypdfium2 as pdfium  # type: ignore
        doc = pdfium.PdfDocument(str(pdf_path))
        try:
            if page_idx_0based < 0 or page_idx_0based >= len(doc):
                raise RuntimeError(f"Page {page_idx_0based + 1} out of range (1..{len(doc)})")
            page = doc[page_idx_0based]
            scale = max(72, min(int(dpi or 200), 600)) / 72.0
            bitmap = page.render(scale=scale)
            pil_img = bitmap.to_pil()
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("ascii")
        finally:
            doc.close()
    except ImportError:
        return base64.b64encode(_FALLBACK_1X1_PNG).decode("ascii")


def safe_extract_archive(
    archive_path: Path,
    dest_dir: Path,
    *,
    max_files: int = 200,
    max_total_bytes: int = 512 * 1024 * 1024,
) -> list[Path]:
    """Safely unpack .zip or .tar.gz/.tgz into dest_dir, rejecting path traversal & bombs."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_real = dest_dir.resolve()
    extracted: list[Path] = []
    total_bytes = 0
    lower_name = archive_path.name.lower()

    if lower_name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            for info in sorted(infos, key=lambda x: x.filename):
                rel = Path(info.filename)
                if any(p.startswith(".") or p == "__MACOSX" for p in rel.parts):
                    continue
                if ".." in rel.parts or info.filename.startswith("/"):
                    raise ValueError(f"Unsafe archive member path: {info.filename}")
                if len(extracted) >= max_files:
                    raise ValueError(f"Archive exceeds max_files_per_task ({max_files})")
                total_bytes += info.file_size
                if total_bytes > max_total_bytes:
                    raise ValueError(f"Archive uncompressed size exceeds limit ({max_total_bytes} bytes)")
                flat_name = "_".join(rel.parts)
                target = (dest_dir / flat_name).resolve()
                if not str(target).startswith(str(dest_real) + os.sep):
                    raise ValueError(f"Unsafe archive member path: {info.filename}")
                with zf.open(info, "r") as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(target)
    elif lower_name.endswith(".tar.gz") or lower_name.endswith(".tgz") or lower_name.endswith(".tar"):
        with tarfile.open(archive_path, "r:*") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            for m in sorted(members, key=lambda x: x.name):
                rel = Path(m.name)
                if any(p.startswith(".") or p == "__MACOSX" for p in rel.parts):
                    continue
                if ".." in rel.parts or m.name.startswith("/"):
                    raise ValueError(f"Unsafe archive member path: {m.name}")
                if len(extracted) >= max_files:
                    raise ValueError(f"Archive exceeds max_files_per_task ({max_files})")
                total_bytes += m.size
                if total_bytes > max_total_bytes:
                    raise ValueError(f"Archive uncompressed size exceeds limit ({max_total_bytes} bytes)")
                flat_name = "_".join(rel.parts)
                target = (dest_dir / flat_name).resolve()
                if not str(target).startswith(str(dest_real) + os.sep):
                    raise ValueError(f"Unsafe archive member path: {m.name}")
                src = tf.extractfile(m)
                if src is not None:
                    with src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    extracted.append(target)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path.name}")

    return extracted


# ---------------------------------------------------------------------------
# Parameter coercion & staging
# ---------------------------------------------------------------------------
def coerce_scalar(val: Any) -> Any:
    if not isinstance(val, str):
        return val
    s = val.strip()
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.lower() == "null" or s.lower() == "none":
        return None
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            return json.loads(s)
        except Exception:
            pass
    if re.fullmatch(r"-?\d+", s):
        try:
            return int(s)
        except Exception:
            pass
    if re.fullmatch(r"-?\d+\.\d+", s):
        try:
            return float(s)
        except Exception:
            pass
    return val


def merge_item_params(
    card: dict[str, Any],
    task_params: dict[str, Any],
    file_params_map: dict[str, Any],
    item_params: dict[str, Any],
    *,
    item_name: str = "",
    item_index: int = 0,
) -> dict[str, Any]:
    """Merge card defaults -> task_params -> file_params[name|index] -> item_params.
    Preserves ALL custom and unlisted parameters.
    """
    merged = extract_card_defaults(card)
    if isinstance(task_params, dict):
        for k, v in task_params.items():
            if v is not None:
                merged[k] = v
    if isinstance(file_params_map, dict):
        for key_candidate in (str(item_index), item_name, Path(item_name).name if item_name else ""):
            if key_candidate and key_candidate in file_params_map and isinstance(file_params_map[key_candidate], dict):
                for k, v in file_params_map[key_candidate].items():
                    if v is not None:
                        merged[k] = v
    if isinstance(item_params, dict):
        for k, v in item_params.items():
            if v is not None:
                merged[k] = v
    return merged


def _unroll_multi_image_items(
    items: list[dict[str, Any]],
    card: dict[str, Any],
    task_params: dict[str, Any],
) -> list[dict[str, Any]]:
    """If an image model caps `n` per call (e.g. max: 1) and caller asks for `n > max_n`,
    unroll into N sequential items with incrementing seed (`seed + i`).
    """
    if str(card.get("type") or "").lower() != "image":
        return items
    props = extract_card_properties(card)
    n_spec = props.get("n") or {}
    max_n = int(n_spec.get("max") or 1)
    unrolled: list[dict[str, Any]] = []
    for it in items:
        ip = dict(it.get("params") or {})
        req_n = int(ip.get("n", task_params.get("n", 1)) or 1)
        if req_n > max_n and max_n == 1:
            base_seed = ip.get("seed", task_params.get("seed"))
            base_name = Path(str(it.get("name") or f"item_{len(unrolled):03d}")).stem
            for sub_i in range(req_n):
                sub_it = copy.deepcopy(it)
                sub_it["name"] = f"{base_name}_{sub_i + 1:03d}"
                sub_params = dict(ip)
                sub_params["n"] = 1
                if isinstance(base_seed, int):
                    sub_params["seed"] = base_seed + sub_i
                sub_it["params"] = sub_params
                unrolled.append(sub_it)
        else:
            unrolled.append(it)
    return unrolled


async def stage_task_submission(
    request: Request,
    store: TaskStore,
    model_cards: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Parse multipart/form-data or application/json task submission, stage inputs on /tasks,
    and return (key_hash, manifest).
    """
    key_hash, owner = extract_caller_identity(request)
    ctype = (request.headers.get("content-type") or "").lower()

    model_id = ""
    task_params: dict[str, Any] = {}
    file_params_map: dict[str, Any] = {}
    raw_inputs: list[dict[str, Any]] = []
    uploaded_files: list[tuple[str, bytes, str]] = []  # (filename, data, content_type)
    envelope_overrides: dict[str, Any] = {}

    if "multipart/form-data" in ctype:
        form = await request.form()
        for key, value in form.multi_items():
            if hasattr(value, "read"):
                fname = _safe_filename(str(getattr(value, "filename", None) or f"upload_{len(uploaded_files):03d}.bin"))
                data = await value.read()
                f_ctype = str(getattr(value, "content_type", "") or "application/octet-stream")
                uploaded_files.append((fname, data, f_ctype))
                continue

            sval = str(value)
            if key == "model":
                model_id = sval.strip()
            elif key == "params":
                parsed = coerce_scalar(sval)
                if isinstance(parsed, dict):
                    task_params.update(parsed)
            elif key == "file_params":
                parsed = coerce_scalar(sval)
                if isinstance(parsed, dict):
                    file_params_map.update(parsed)
            elif key == "inputs":
                parsed = coerce_scalar(sval)
                if isinstance(parsed, list):
                    raw_inputs.extend(x for x in parsed if isinstance(x, dict))
            elif key in ENVELOPE_KEY_SET:
                envelope_overrides[key] = coerce_scalar(sval)
            else:
                task_params[key] = coerce_scalar(sval)
    else:
        try:
            body = await request.json()
        except Exception as e:
            raise HTTPException(400, detail={"error": {"message": f"Invalid JSON body: {e}", "type": "invalid_request_error"}})
        if not isinstance(body, dict):
            raise HTTPException(400, detail={"error": {"message": "Request body must be a JSON object", "type": "invalid_request_error"}})

        model_id = str(body.get("model") or "").strip()
        if isinstance(body.get("params"), dict):
            task_params.update(body["params"])
        if isinstance(body.get("file_params"), dict):
            file_params_map.update(body["file_params"])
        if isinstance(body.get("inputs"), list):
            for x in body["inputs"]:
                if isinstance(x, dict):
                    raw_inputs.append(x)
                elif isinstance(x, str):
                    raw_inputs.append({"prompt": x})

        for k, v in body.items():
            if k in ("model", "params", "file_params", "inputs"):
                continue
            if k in ENVELOPE_KEY_SET:
                envelope_overrides[k] = v
            else:
                task_params[k] = v

    if not model_id:
        raise HTTPException(400, detail={"error": {"message": "Missing required field 'model'", "type": "invalid_request_error"}})

    card = model_cards.get(model_id)
    if not card:
        raise HTTPException(
            404,
            detail={
                "error": {
                    "message": f"Unknown model '{model_id}'. Query GET /v1/models?all=true or GET /v1/tasks/models for available models.",
                    "type": "model_not_found",
                }
            },
        )

    tinfo = build_task_info(card)
    limits = tinfo["limits"]

    active_cnt = store.count_active_tasks(key_hash)
    if active_cnt >= int(limits["max_active_tasks_per_user"]):
        raise HTTPException(
            429,
            detail={
                "error": {
                    "message": f"Too many active tasks ({active_cnt}/{limits['max_active_tasks_per_user']}) for this API key.",
                    "type": "rate_limit_exceeded",
                }
            },
        )

    max_upload_bytes = int(limits["max_upload_mb"]) * 1024 * 1024
    total_upload_bytes = sum(len(d) for _, d, _ in uploaded_files)
    if total_upload_bytes > max_upload_bytes:
        raise HTTPException(
            413,
            detail={
                "error": {
                    "message": f"Total upload size ({total_upload_bytes} bytes) exceeds limit ({limits['max_upload_mb']} MB).",
                    "type": "payload_too_large",
                }
            },
        )

    task_id = _new_task_id()
    loop_mode = str(envelope_overrides.get("loop_mode") or tinfo["loop_mode"])
    file_grouping = str(envelope_overrides.get("file_grouping") or tinfo["file_grouping"])
    unpack_archive = bool(envelope_overrides.get("unpack_archive", False))
    continue_on_item_error = bool(envelope_overrides.get("continue_on_item_error", True))
    notify_email = str(envelope_overrides.get("notify_email") or "").strip() or None
    endpoint_override = str(envelope_overrides.get("endpoint") or "").strip() or None

    now_str = _iso_now()
    manifest: dict[str, Any] = {
        "task_id": task_id,
        "object": "task",
        "model": model_id,
        "mode": tinfo["mode"],
        "owner": owner,
        "key_hash": key_hash,
        "status": "queued",
        "loop_mode": loop_mode,
        "file_grouping": file_grouping,
        "continue_on_item_error": continue_on_item_error,
        "endpoint": endpoint_override,
        "notify_email": notify_email,
        "email_sent": False,
        "created_at": now_str,
        "started_at": None,
        "completed_at": None,
        "expires_at": None,
        "retention_hours": tinfo["retention_hours"],
        "unit": tinfo["unit"],
        "total_units": 0,
        "completed_units": 0,
        "failed_units": 0,
        "current_item": None,
        "avg_unit_seconds": None,
        "eta_seconds": None,
        "params": merge_item_params(card, task_params, {}, {}),
        "file_params": file_params_map,
        "input_files": [],
        "output_files": [],
        "errors": [],
        "error_count": 0,
        "last_error": None,
        "error_log_url": f"/v1/tasks/{task_id}/error.log",
        "result_url": f"/v1/tasks/{task_id}/result",
        "_items": [],
    }
    tdir = store.create_task(key_hash, manifest)
    in_dir = tdir / "in"

    staged_paths: list[Path] = []
    for idx, (fname, data, _) in enumerate(uploaded_files):
        safe_name = _safe_filename(fname, default=f"input_{idx:03d}.bin")
        dest = in_dir / safe_name
        if dest.exists():
            dest = in_dir / f"{dest.stem}_{idx:03d}{dest.suffix}"
        dest.write_bytes(data)
        lower = dest.name.lower()
        if unpack_archive and (lower.endswith(".zip") or lower.endswith(".tar.gz") or lower.endswith(".tgz") or lower.endswith(".tar")):
            try:
                unpacked = safe_extract_archive(
                    dest,
                    in_dir,
                    max_files=int(limits["max_files_per_task"]),
                    max_total_bytes=max_upload_bytes,
                )
                dest.unlink(missing_ok=True)
                staged_paths.extend(unpacked)
            except Exception as e:
                store.delete_task_files(key_hash, task_id)
                raise HTTPException(400, detail={"error": {"message": f"Archive extraction failed: {e}", "type": "invalid_request_error"}})
        else:
            staged_paths.append(dest)

    if len(staged_paths) > int(limits["max_files_per_task"]):
        store.delete_task_files(key_hash, task_id)
        raise HTTPException(
            400,
            detail={
                "error": {
                    "message": f"Task contains {len(staged_paths)} files, exceeding max_files_per_task ({limits['max_files_per_task']}).",
                    "type": "invalid_request_error",
                }
            },
        )

    manifest["input_files"] = [p.name for p in staged_paths]

    # Build ordered execution items (_items)
    items: list[dict[str, Any]] = []
    mtype = str(card.get("type") or "chat").lower()

    if staged_paths:
        if file_grouping == "bundle":
            items.append(
                {
                    "name": "bundle",
                    "kind": "bundle_files",
                    "files": [p.name for p in staged_paths],
                    "params": {},
                }
            )
        else:
            for f_idx, p in enumerate(staged_paths):
                ext = p.suffix.lower()
                if ext == ".jsonl" and mtype in ("image", "chat", "audio", "3d", "custom"):
                    lines = [ln.strip() for ln in p.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
                    for l_idx, ln in enumerate(lines):
                        try:
                            obj = json.loads(ln)
                        except Exception:
                            obj = {"prompt": ln}
                        items.append(
                            {
                                "name": str(obj.get("name") or f"{p.stem}_{l_idx + 1:03d}"),
                                "kind": "json_item",
                                "payload": obj,
                                "params": obj if isinstance(obj, dict) else {},
                            }
                        )
                elif ext == ".txt" and mtype == "image":
                    lines = [ln.strip() for ln in p.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip() and not ln.strip().startswith("#")]
                    for l_idx, ln in enumerate(lines):
                        items.append(
                            {
                                "name": f"{p.stem}_{l_idx + 1:03d}",
                                "kind": "json_item",
                                "payload": {"prompt": ln},
                                "params": {"prompt": ln},
                            }
                        )
                elif ext == ".pdf" or (loop_mode == "pdf_pages" and ext == ".pdf"):
                    items.append(
                        {
                            "name": p.name,
                            "kind": "pdf_file",
                            "file": p.name,
                            "file_index": f_idx,
                            "params": {},
                        }
                    )
                else:
                    items.append(
                        {
                            "name": p.name,
                            "kind": "single_file",
                            "file": p.name,
                            "file_index": f_idx,
                            "params": {},
                        }
                    )

    for r_idx, raw in enumerate(raw_inputs):
        r_copy = dict(raw)
        iname = _safe_filename(str(r_copy.pop("name", None) or f"item_{len(items) + 1:03d}"), default=f"item_{len(items) + 1:03d}")
        if "pdf_base64" in r_copy:
            b64_str = str(r_copy.pop("pdf_base64"))
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            pdf_name = iname if iname.lower().endswith(".pdf") else f"{iname}.pdf"
            pdf_path = in_dir / pdf_name
            pdf_path.write_bytes(base64.b64decode(b64_str))
            manifest["input_files"].append(pdf_name)
            items.append(
                {
                    "name": pdf_name,
                    "kind": "pdf_file",
                    "file": pdf_name,
                    "file_index": r_idx,
                    "params": r_copy,
                }
            )
        else:
            items.append(
                {
                    "name": iname,
                    "kind": "json_item",
                    "payload": r_copy,
                    "file_index": r_idx,
                    "params": r_copy,
                }
            )

    if not items and task_params:
        items.append(
            {
                "name": "item_001",
                "kind": "json_item",
                "payload": dict(task_params),
                "file_index": 0,
                "params": dict(task_params),
            }
        )

    if not items:
        store.delete_task_files(key_hash, task_id)
        raise HTTPException(
            400,
            detail={
                "error": {
                    "message": "Task submission requires at least one uploaded file (`files`), `inputs` array item, or model input parameters.",
                    "type": "invalid_request_error",
                }
            },
        )

    items = _unroll_multi_image_items(items, card, task_params)

    total_units = 0
    max_pages_per_pdf = int(limits["max_pages_per_pdf"])
    if loop_mode == "rollout_steps":
        merged_top = merge_item_params(card, task_params, file_params_map, items[0].get("params") or {})
        steps = int(merged_top.get("steps") or merged_top.get("rollout_steps") or len(items) or 1)
        total_units = max(1, steps)
    else:
        for idx, it in enumerate(items):
            if it.get("kind") == "pdf_file":
                pdf_p = in_dir / str(it["file"])
                try:
                    num_p = count_pdf_pages(pdf_p)
                except Exception as e:
                    log.warning(f"PDF page count warning on {pdf_p.name}: {e}")
                    it["_pdf_error"] = str(e)
                    it["_page_indices"] = [0]
                    total_units += 1
                    continue
                if num_p > max_pages_per_pdf:
                    store.delete_task_files(key_hash, task_id)
                    raise HTTPException(
                        400,
                        detail={
                            "error": {
                                "message": f"PDF '{pdf_p.name}' has {num_p} pages, exceeding max_pages_per_pdf ({max_pages_per_pdf}). Use `pages` parameter to select a range.",
                                "type": "invalid_request_error",
                            }
                        },
                    )
                item_merged = merge_item_params(
                    card,
                    task_params,
                    file_params_map,
                    it.get("params") or {},
                    item_name=str(it["name"]),
                    item_index=idx,
                )
                page_indices = parse_page_range(item_merged.get("pages"), num_p)
                if not page_indices:
                    page_indices = list(range(num_p))
                it["_page_indices"] = page_indices
                it["_total_pdf_pages"] = num_p
                total_units += len(page_indices)
            else:
                total_units += 1

    manifest["total_units"] = max(1, total_units)
    manifest["eta_seconds"] = round(manifest["total_units"] * float(tinfo["default_unit_seconds"]), 1)
    manifest["_items"] = items
    manifest["_raw_task_params"] = task_params
    store.save_manifest(key_hash, task_id, manifest)
    await store.enqueue(key_hash, task_id)
    return key_hash, manifest


# ---------------------------------------------------------------------------
# Opt-in email notification & result.zip packaging
# ---------------------------------------------------------------------------
def send_task_completion_email(manifest: dict[str, Any]) -> bool:
    """Send opt-in completion email ONLY when notify_email is set on the task
    and TASK_SMTP_HOST is configured in the environment.
    """
    to_addr = (manifest.get("notify_email") or "").strip()
    smtp_host = (os.environ.get("TASK_SMTP_HOST") or "").strip()
    if not to_addr or not smtp_host:
        return False

    smtp_port = int(os.environ.get("TASK_SMTP_PORT") or "25")
    from_user = (os.environ.get("TASK_SMTP_FROM_USER") or "aleph").strip()
    from_domain = (os.environ.get("TASK_SMTP_FROM_DOMAIN") or "localhost").strip()
    from_addr = f"{from_user}@{from_domain}"
    public_url = (os.environ.get("PUBLIC_BASE_URL") or "https://inference.vulcan.alliancecan.ca").rstrip("/")

    tid = manifest.get("task_id", "")
    model = manifest.get("model", "")
    status = manifest.get("status", "completed")
    comp = manifest.get("completed_units", 0)
    tot = manifest.get("total_units", 0)
    err_cnt = manifest.get("error_count", 0)
    exp = manifest.get("expires_at", "")

    msg = EmailMessage()
    msg["From"] = f"Aleph Inference <{from_addr}>"
    msg["To"] = to_addr
    msg["Subject"] = f"[Aleph Task {status.upper()}] {model} ({tid})"
    msg.set_content(
        f"Your Aleph asynchronous task has finished.\n\n"
        f"  Task ID:         {tid}\n"
        f"  Model:           {model}\n"
        f"  Status:          {status}\n"
        f"  Completed Units: {comp} / {tot}\n"
        f"  Errors:          {err_cnt}\n"
        f"  Expires At:      {exp} (24h post-completion retention)\n\n"
        f"Download results (.zip):\n"
        f"  curl -sS -L {public_url}/v1/tasks/{tid}/result -H \"Authorization: Bearer $KEY\" -o {tid}.zip\n\n"
        f"Inspect task status:\n"
        f"  curl -sS {public_url}/v1/tasks/{tid} -H \"Authorization: Bearer $KEY\"\n"
        + (
            f"\nInspect error log:\n"
            f"  curl -sS {public_url}/v1/tasks/{tid}/error.log -H \"Authorization: Bearer $KEY\"\n"
            if err_cnt > 0
            else ""
        )
    )
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.send_message(msg)
        return True
    except Exception as e:
        log.warning(f"Opt-in email notification failed for {tid}: {e}")
        return False


def build_result_zip(store: TaskStore, key_hash: str, task_id: str) -> Path:
    """Package manifest.json, out/*, and error.log (if non-empty) into result.zip."""
    tdir = store.task_dir(key_hash, task_id)
    out_dir = tdir / "out"
    zpath = store.result_zip_path(key_hash, task_id)
    tmp_zip = tdir / f".result.zip.tmp.{os.getpid()}"
    with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        mpath = store.manifest_path(key_hash, task_id)
        if mpath.is_file():
            m = store.load_manifest(key_hash, task_id) or {}
            pub_m = store.public_manifest_view(m)
            zf.writestr("manifest.json", json.dumps(pub_m, indent=2))
        epath = store.error_log_path(key_hash, task_id)
        if epath.is_file() and epath.stat().st_size > 0:
            zf.write(epath, arcname="error.log")
        if out_dir.is_dir():
            for p in sorted(out_dir.iterdir(), key=lambda x: x.name):
                if p.is_file():
                    zf.write(p, arcname=f"out/{p.name}")
    tmp_zip.replace(zpath)
    return zpath


# ---------------------------------------------------------------------------
# Sequential 1-by-1 execution engine
# ---------------------------------------------------------------------------
TASK_INTERNAL_PARAM_KEYS = frozenset(
    {
        "dpi",
        "pages",
        "output_format",
        "loop_mode",
        "file_grouping",
        "unpack_archive",
        "continue_on_item_error",
        "notify_email",
        "endpoint",
    }
)


def _guess_image_mime(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
    }.get(ext, "image/png")


def _extract_chat_text(resp_json: dict[str, Any]) -> str:
    choices = resp_json.get("choices") or []
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        if isinstance(msg, dict) and msg.get("content") is not None:
            return str(msg.get("content"))
        if choices[0].get("text") is not None:
            return str(choices[0].get("text"))
    if resp_json.get("text") is not None:
        return str(resp_json["text"])
    return json.dumps(resp_json)


async def _post_predictor_json(
    http_client: httpx.AsyncClient | None,
    url: str,
    payload: dict[str, Any],
    *,
    host_header: str | None = None,
    timeout_s: float = 600.0,
) -> tuple[int, dict[str, Any] | None, str]:
    headers = {"Content-Type": "application/json"}
    if host_header:
        headers["Host"] = host_header
    encoded = json.dumps(payload).encode("utf-8")
    if http_client is not None:
        resp = await http_client.post(url, content=encoded, headers=headers, timeout=timeout_s)
    else:
        async with httpx.AsyncClient(timeout=timeout_s) as c:
            resp = await c.post(url, content=encoded, headers=headers)
    text = resp.text
    if resp.status_code >= 400:
        return resp.status_code, None, text
    try:
        return resp.status_code, resp.json(), text
    except Exception:
        return resp.status_code, {"raw": text}, text


async def execute_task(
    store: TaskStore,
    key_hash: str,
    task_id: str,
    runtime_hooks: dict[str, Any],
) -> dict[str, Any] | None:
    """Execute a queued task sequentially 1-by-1 against the warm predictor pod.

    runtime_hooks keys:
      - get_card(model_id) -> dict | None
      - ensure_predictor_ready(model_id, card) -> str | tuple[str, str]
        (returns predictor base URL, or (base_url, host_header))
      - active_sync_requests(model_id) -> int
      - prepare_chat(info, body) -> (body, thinking_on) [optional]
      - http_client -> httpx.AsyncClient | None
      - record_usage(model_id, card, status, latency_ms, usage_obj) [optional]
    """
    manifest = store.load_manifest(key_hash, task_id)
    if not manifest:
        return None
    if manifest.get("status") in TERMINAL_TASK_STATUSES:
        return manifest

    model_id = manifest["model"]
    get_card: Callable[[str], dict | None] = runtime_hooks["get_card"]
    ensure_predictor_ready: Callable[[str, dict], Any] = runtime_hooks["ensure_predictor_ready"]
    active_sync_fn: Callable[[str], int] = runtime_hooks.get("active_sync_requests", lambda _: 0)
    prepare_chat_fn = runtime_hooks.get("prepare_chat")
    http_client: httpx.AsyncClient | None = runtime_hooks.get("http_client")
    record_usage_fn = runtime_hooks.get("record_usage")

    card = get_card(model_id)
    if not card:
        err = store.append_error_log(
            key_hash,
            task_id,
            item="task_init",
            stage="lookup_model",
            message=f"Model card '{model_id}' not found",
        )
        manifest["status"] = "failed"
        manifest["errors"].append(err)
        manifest["error_count"] = len(manifest["errors"])
        manifest["last_error"] = err
        now_dt = _utc_now()
        manifest["completed_at"] = _iso_now()
        manifest["expires_at"] = (now_dt + timedelta(hours=int(manifest.get("retention_hours") or 24))).strftime("%Y-%m-%dT%H:%M:%SZ")
        store.save_manifest(key_hash, task_id, manifest)
        build_result_zip(store, key_hash, task_id)
        return manifest

    tinfo = build_task_info(card)
    yield_seconds = float(tinfo.get("yield_to_sync_seconds") or 0.0)
    timeout_s = float((tinfo.get("limits") or {}).get("timeout_seconds") or 3600.0)
    continue_on_error = bool(manifest.get("continue_on_item_error", True))
    loop_mode = str(manifest.get("loop_mode") or tinfo["loop_mode"])
    mtype = str(card.get("type") or "chat").lower()
    routing = (card.get("routing") or {}) if isinstance(card.get("routing"), dict) else {}
    endpoints = (card.get("endpoints") or {}) if isinstance(card.get("endpoints"), dict) else {}
    k8s_name = routing.get("k8s_name") or model_id
    models_ns = os.environ.get("MODELS_NAMESPACE", "models")
    default_host_hdr = f"{k8s_name}-predictor.{models_ns}.svc.cluster.local"

    tdir = store.task_dir(key_hash, task_id)
    in_dir = tdir / "in"
    out_dir = tdir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Transition to waking_pod and wait for GPU capacity + warm predictor once before item 0
    manifest["status"] = "waking_pod"
    if not manifest.get("started_at"):
        manifest["started_at"] = _iso_now()
    store.save_manifest(key_hash, task_id, manifest)

    try:
        ready_res = await ensure_predictor_ready(model_id, card)
        if isinstance(ready_res, tuple):
            predictor_base_url, host_hdr = ready_res[0], ready_res[1]
        else:
            predictor_base_url, host_hdr = str(ready_res), default_host_hdr
    except Exception as e:
        tb = traceback.format_exc()
        err = store.append_error_log(
            key_hash,
            task_id,
            item="waking_pod",
            stage="wake_predictor",
            message=f"Failed to wake or schedule predictor for '{model_id}': {e}",
            exc_tb=tb,
        )
        manifest["status"] = "failed"
        manifest["errors"].append(err)
        manifest["error_count"] = len(manifest["errors"])
        manifest["last_error"] = err
        now_dt = _utc_now()
        manifest["completed_at"] = _iso_now()
        manifest["expires_at"] = (now_dt + timedelta(hours=int(manifest.get("retention_hours") or 24))).strftime("%Y-%m-%dT%H:%M:%SZ")
        store.save_manifest(key_hash, task_id, manifest)
        build_result_zip(store, key_hash, task_id)
        if manifest.get("notify_email"):
            manifest["email_sent"] = send_task_completion_email(manifest)
            store.save_manifest(key_hash, task_id, manifest)
        return manifest

    latest_m = store.load_manifest(key_hash, task_id)
    if latest_m and latest_m.get("status") == "cancelled":
        return latest_m

    manifest["status"] = "running"
    store.save_manifest(key_hash, task_id, manifest)

    items: list[dict[str, Any]] = list(manifest.get("_items") or [])
    raw_task_params: dict[str, Any] = dict(manifest.get("_raw_task_params") or manifest.get("params") or {})
    file_params_map: dict[str, Any] = dict(manifest.get("file_params") or {})

    unit_durations: list[float] = []

    def _record_output_file(fname: str) -> None:
        if fname not in manifest["output_files"]:
            manifest["output_files"].append(fname)

    def _checkpoint_unit(unit_elapsed: float | None = None, failed: bool = False, usage_obj: dict | None = None) -> None:
        if failed:
            manifest["failed_units"] = int(manifest.get("failed_units") or 0) + 1
        else:
            manifest["completed_units"] = int(manifest.get("completed_units") or 0) + 1
        if unit_elapsed is not None and unit_elapsed >= 0:
            unit_durations.append(unit_elapsed)
        if unit_durations:
            avg_s = sum(unit_durations) / len(unit_durations)
        else:
            avg_s = float(tinfo["default_unit_seconds"])
        manifest["avg_unit_seconds"] = round(avg_s, 3)
        done = int(manifest.get("completed_units") or 0) + int(manifest.get("failed_units") or 0)
        rem = max(0, int(manifest.get("total_units") or 0) - done)
        manifest["eta_seconds"] = round(rem * avg_s, 1)
        manifest["error_count"] = len(manifest.get("errors") or [])
        manifest["last_error"] = manifest["errors"][-1] if manifest.get("errors") else None
        store.save_manifest(key_hash, task_id, manifest)
        if record_usage_fn and unit_elapsed is not None:
            try:
                record_usage_fn(model_id, card, 500 if failed else 200, int(unit_elapsed * 1000), usage_obj)
            except Exception:
                pass

    async def _maybe_yield_to_sync() -> None:
        if yield_seconds > 0 and active_sync_fn(model_id) > 0:
            await asyncio.sleep(yield_seconds)

    def _is_cancelled() -> bool:
        cur = store.load_manifest(key_hash, task_id)
        if cur and cur.get("status") == "cancelled":
            manifest["status"] = "cancelled"
            return True
        return False

    # -----------------------------------------------------------------------
    # Mode A: Rollout steps (sequential step 1 -> step N chaining)
    # -----------------------------------------------------------------------
    if loop_mode == "rollout_steps":
        total_steps = int(manifest.get("total_units") or 1)
        base_item = items[0] if items else {"name": "rollout", "kind": "json_item", "payload": {}, "params": {}}
        merged_params = merge_item_params(card, raw_task_params, file_params_map, base_item.get("params") or {}, item_name="rollout", item_index=0)
        upstream_path = routing.get("upstream_path") or endpoints.get("primary") or "/v1/forecast"
        if upstream_path == "/v1/tasks":
            upstream_path = "/v1/forecast"
        target_url = f"{predictor_base_url.rstrip('/')}{upstream_path}"

        current_state: Any = merged_params.get("initial_state") or (base_item.get("payload") or {}).get("initial_state")
        if current_state is None and base_item.get("kind") == "single_file":
            fp = in_dir / str(base_item["file"])
            if fp.suffix.lower() == ".json":
                try:
                    current_state = json.loads(fp.read_text(encoding="utf-8"))
                except Exception:
                    current_state = base64.b64encode(fp.read_bytes()).decode("ascii")
            else:
                current_state = base64.b64encode(fp.read_bytes()).decode("ascii")

        step_outputs: list[str] = []
        for step_idx in range(1, total_steps + 1):
            if _is_cancelled():
                break
            await _maybe_yield_to_sync()
            item_label = f"step_{step_idx:03d}"
            manifest["current_item"] = item_label
            store.save_manifest(key_hash, task_id, manifest)
            t0 = time.monotonic()
            try:
                step_payload = {
                    k: v for k, v in merged_params.items() if k not in TASK_INTERNAL_PARAM_KEYS
                }
                step_payload["step_index"] = step_idx
                if current_state is not None:
                    step_payload["initial_state"] = current_state
                forwarded = prepare_custom_payload(step_payload, card)
                status_code, resp_json, raw_text = await _post_predictor_json(
                    http_client, target_url, forwarded, host_header=host_hdr, timeout_s=timeout_s
                )
                if status_code >= 400 or resp_json is None:
                    raise RuntimeError(f"Upstream HTTP {status_code}: {raw_text[:1000]}")
                step_fname = f"step_{step_idx:03d}.json"
                (out_dir / step_fname).write_text(json.dumps(resp_json, indent=2), encoding="utf-8")
                _record_output_file(step_fname)
                step_outputs.append(step_fname)
                if isinstance(resp_json, dict):
                    current_state = (
                        resp_json.get("next_state")
                        or resp_json.get("output_state")
                        or resp_json.get("prediction")
                        or resp_json
                    )
                _checkpoint_unit(time.monotonic() - t0, failed=False)
            except Exception as e:
                tb = traceback.format_exc()
                err = store.append_error_log(
                    key_hash,
                    task_id,
                    item=item_label,
                    stage="rollout_step",
                    message=str(e),
                    exc_tb=tb,
                )
                manifest["errors"].append(err)
                _checkpoint_unit(time.monotonic() - t0, failed=True)
                if not continue_on_error:
                    break

        summary_fname = "rollout_summary.json"
        (out_dir / summary_fname).write_text(
            json.dumps({"model": model_id, "steps_requested": total_steps, "step_files": step_outputs}, indent=2),
            encoding="utf-8",
        )
        _record_output_file(summary_fname)

    # -----------------------------------------------------------------------
    # Mode B: Item-by-item & PDF page-by-page sequential loop (1 -> 2 -> ... -> N)
    # -----------------------------------------------------------------------
    else:
        for idx, item in enumerate(items):
            if _is_cancelled():
                break

            item_name = str(item.get("name") or f"item_{idx + 1:03d}")
            item_kind = str(item.get("kind") or "json_item")
            item_params = merge_item_params(
                card,
                raw_task_params,
                file_params_map,
                item.get("params") or {},
                item_name=item_name,
                item_index=int(item.get("file_index", idx)),
            )

            # --- Sub-case B1: PDF file processed page-by-page ---
            if item_kind == "pdf_file":
                pdf_fname = str(item["file"])
                pdf_path = in_dir / pdf_fname
                stem = Path(pdf_fname).stem
                if item.get("_pdf_error"):
                    err = store.append_error_log(
                        key_hash,
                        task_id,
                        item=pdf_fname,
                        stage="pdf_open",
                        message=str(item["_pdf_error"]),
                    )
                    manifest["errors"].append(err)
                    _checkpoint_unit(0.0, failed=True)
                    if not continue_on_error:
                        break
                    continue

                page_indices: list[int] = list(item.get("_page_indices") or [0])
                dpi = int(item_params.get("dpi") or 200)
                prompt_text = str(item_params.get("prompt") or "Text Recognition:")
                upstream_path = routing.get("upstream_path") or "/v1/chat/completions"
                if upstream_path == "/v1/tasks":
                    upstream_path = "/v1/chat/completions"
                target_url = f"{predictor_base_url.rstrip('/')}{upstream_path}"

                doc_pages_out: list[dict[str, Any]] = []
                doc_md_parts: list[str] = []

                for p_idx0 in page_indices:
                    if _is_cancelled():
                        break
                    await _maybe_yield_to_sync()
                    page_num_1based = p_idx0 + 1
                    page_label = f"{pdf_fname}#page={page_num_1based}"
                    manifest["current_item"] = page_label
                    store.save_manifest(key_hash, task_id, manifest)
                    t0 = time.monotonic()
                    try:
                        img_b64 = render_pdf_page_png_b64(pdf_path, p_idx0, dpi=dpi)
                        # GLM-OCR / vLLM vision best practice: image_url content block BEFORE text prompt
                        chat_body: dict[str, Any] = {
                            k: v
                            for k, v in item_params.items()
                            if k not in TASK_INTERNAL_PARAM_KEYS and k != "prompt"
                        }
                        chat_body["model"] = model_id
                        chat_body["messages"] = [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                                    },
                                    {
                                        "type": "text",
                                        "text": prompt_text,
                                    },
                                ],
                            }
                        ]
                        prepared_body = prepare_chat_payload(chat_body, card, prepare_chat_fn=prepare_chat_fn)
                        status_code, resp_json, raw_text = await _post_predictor_json(
                            http_client, target_url, prepared_body, host_header=host_hdr, timeout_s=timeout_s
                        )
                        if status_code >= 400 or resp_json is None:
                            raise RuntimeError(f"Upstream HTTP {status_code}: {raw_text[:1000]}")
                        page_text = _extract_chat_text(resp_json)
                        elapsed = round(time.monotonic() - t0, 3)

                        page_md_name = f"{stem}_page_{page_num_1based:03d}.md"
                        (out_dir / page_md_name).write_text(page_text, encoding="utf-8")
                        _record_output_file(page_md_name)

                        page_rec = {
                            "file": pdf_fname,
                            "page": page_num_1based,
                            "prompt": prompt_text,
                            "dpi": dpi,
                            "markdown": page_text,
                            "elapsed_seconds": elapsed,
                            "usage": resp_json.get("usage"),
                        }
                        doc_pages_out.append(page_rec)
                        doc_md_parts.append(f"<!-- Page {page_num_1based} -->\n{page_text}")
                        _checkpoint_unit(elapsed, failed=False, usage_obj=resp_json.get("usage"))
                    except Exception as e:
                        tb = traceback.format_exc()
                        err = store.append_error_log(
                            key_hash,
                            task_id,
                            item=page_label,
                            stage="ocr_page",
                            message=str(e),
                            exc_tb=tb,
                        )
                        manifest["errors"].append(err)
                        _checkpoint_unit(time.monotonic() - t0, failed=True)
                        if not continue_on_error:
                            break

                if doc_md_parts:
                    full_md_name = f"{stem}.md"
                    (out_dir / full_md_name).write_text("\n\n---\n\n".join(doc_md_parts) + "\n", encoding="utf-8")
                    _record_output_file(full_md_name)
                if doc_pages_out:
                    full_json_name = f"{stem}.json"
                    (out_dir / full_json_name).write_text(
                        json.dumps(
                            {
                                "file": pdf_fname,
                                "model": model_id,
                                "total_pages_processed": len(doc_pages_out),
                                "pages": doc_pages_out,
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    _record_output_file(full_json_name)
                continue

            # --- Sub-case B2: Non-PDF single item / image / custom / chat ---
            await _maybe_yield_to_sync()
            manifest["current_item"] = item_name
            store.save_manifest(key_hash, task_id, manifest)
            t0 = time.monotonic()

            try:
                stem = Path(item_name).stem or f"item_{idx + 1:03d}"

                # 1) OCR or Chat/VLM model (uses vLLM /v1/chat/completions + prepare_chat_payload)
                if mtype in ("ocr", "chat") or (routing.get("upstream_path") == "/v1/chat/completions"):
                    upstream_path = routing.get("upstream_path") or "/v1/chat/completions"
                    if upstream_path == "/v1/tasks":
                        upstream_path = "/v1/chat/completions"
                    target_url = f"{predictor_base_url.rstrip('/')}{upstream_path}"
                    prompt_text = str(item_params.get("prompt") or ("Text Recognition:" if mtype == "ocr" else "Hello"))

                    chat_body = {
                        k: v
                        for k, v in item_params.items()
                        if k not in TASK_INTERNAL_PARAM_KEYS and k not in ("prompt", "image_base64", "image_url", "image")
                    }
                    chat_body["model"] = model_id

                    if "messages" not in chat_body:
                        content_blocks: list[dict[str, Any]] = []
                        if item_kind == "single_file":
                            fpath = in_dir / str(item["file"])
                            ext = fpath.suffix.lower()
                            if ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp", ".gif"):
                                b64 = base64.b64encode(fpath.read_bytes()).decode("ascii")
                                mime = _guess_image_mime(fpath.name)
                                content_blocks.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
                            else:
                                txt_content = fpath.read_text(encoding="utf-8", errors="replace")
                                prompt_text = f"{prompt_text}\n\n{txt_content}" if prompt_text else txt_content
                        elif item_kind == "bundle_files":
                            for bfname in item.get("files") or []:
                                fpath = in_dir / str(bfname)
                                b64 = base64.b64encode(fpath.read_bytes()).decode("ascii")
                                mime = _guess_image_mime(fpath.name)
                                content_blocks.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
                        else:
                            b64_inline = item_params.get("image_base64") or item_params.get("image")
                            img_url_inline = item_params.get("image_url")
                            if b64_inline:
                                data_uri = b64_inline if str(b64_inline).startswith("data:") else f"data:image/png;base64,{b64_inline}"
                                content_blocks.append({"type": "image_url", "image_url": {"url": data_uri}})
                            elif img_url_inline:
                                url_str = img_url_inline["url"] if isinstance(img_url_inline, dict) else str(img_url_inline)
                                content_blocks.append({"type": "image_url", "image_url": {"url": url_str}})

                        if content_blocks:
                            content_blocks.append({"type": "text", "text": prompt_text})
                            chat_body["messages"] = [{"role": "user", "content": content_blocks}]
                        else:
                            chat_body["messages"] = [{"role": "user", "content": prompt_text}]

                    prepared_body = prepare_chat_payload(chat_body, card, prepare_chat_fn=prepare_chat_fn)
                    status_code, resp_json, raw_text = await _post_predictor_json(
                        http_client, target_url, prepared_body, host_header=host_hdr, timeout_s=timeout_s
                    )
                    if status_code >= 400 or resp_json is None:
                        raise RuntimeError(f"Upstream HTTP {status_code}: {raw_text[:1000]}")

                    out_text = _extract_chat_text(resp_json)
                    md_name = f"{stem}.md"
                    json_name = f"{stem}.json"
                    (out_dir / md_name).write_text(out_text, encoding="utf-8")
                    (out_dir / json_name).write_text(
                        json.dumps(
                            {
                                "item": item_name,
                                "model": model_id,
                                "prompt": prompt_text,
                                "markdown": out_text,
                                "response": resp_json,
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    _record_output_file(md_name)
                    _record_output_file(json_name)
                    _checkpoint_unit(time.monotonic() - t0, failed=False, usage_obj=resp_json.get("usage"))

                # 2) Image generation / image editing model (uses prepare_custom_payload)
                elif mtype == "image":
                    payload = {
                        k: v for k, v in item_params.items() if k not in TASK_INTERNAL_PARAM_KEYS
                    }
                    has_image_input = False
                    if item_kind == "single_file":
                        fpath = in_dir / str(item["file"])
                        b64 = base64.b64encode(fpath.read_bytes()).decode("ascii")
                        imap = card.get("input_map") or {}
                        if "images" in imap and "image" not in imap:
                            payload["images"] = [b64]
                        else:
                            payload["image"] = b64
                        has_image_input = True
                    elif item_kind == "bundle_files":
                        b64_list = [
                            base64.b64encode((in_dir / str(fn)).read_bytes()).decode("ascii")
                            for fn in (item.get("files") or [])
                        ]
                        payload["images"] = b64_list
                        has_image_input = True
                    elif any(k in payload for k in ("image", "image_b64", "images")):
                        has_image_input = True

                    ep_choice = manifest.get("endpoint")
                    if (ep_choice == "edit" or has_image_input) and endpoints.get("edit"):
                        upstream_path = str(endpoints["edit"])
                    else:
                        upstream_path = str(routing.get("upstream_path") or endpoints.get("primary") or "/v1/images/generations")
                    if upstream_path == "/v1/tasks":
                        upstream_path = "/v1/images/generations"

                    forwarded = prepare_custom_payload(payload, card)
                    target_url = f"{predictor_base_url.rstrip('/')}{upstream_path}"
                    status_code, resp_json, raw_text = await _post_predictor_json(
                        http_client, target_url, forwarded, host_header=host_hdr, timeout_s=timeout_s
                    )
                    if status_code >= 400 or resp_json is None:
                        raise RuntimeError(f"Upstream HTTP {status_code}: {raw_text[:1000]}")

                    images_b64: list[str] = []
                    if isinstance(resp_json.get("data"), list):
                        for d_item in resp_json["data"]:
                            if isinstance(d_item, dict) and d_item.get("b64_json"):
                                images_b64.append(str(d_item["b64_json"]))
                    elif resp_json.get("b64_json"):
                        images_b64.append(str(resp_json["b64_json"]))
                    elif resp_json.get("image_base64"):
                        images_b64.append(str(resp_json["image_base64"]))

                    saved_pngs: list[str] = []
                    for img_i, b64_str in enumerate(images_b64):
                        png_name = f"{stem}.png" if len(images_b64) == 1 else f"{stem}_{img_i + 1:02d}.png"
                        (out_dir / png_name).write_bytes(base64.b64decode(b64_str))
                        _record_output_file(png_name)
                        saved_pngs.append(png_name)

                    meta_name = f"{stem}.meta.json"
                    (out_dir / meta_name).write_text(
                        json.dumps(
                            {
                                "item": item_name,
                                "model": model_id,
                                "endpoint": upstream_path,
                                "params": {k: v for k, v in forwarded.items() if k not in ("image", "images", "image_b64")},
                                "files": saved_pngs,
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    _record_output_file(meta_name)
                    _checkpoint_unit(time.monotonic() - t0, failed=False)

                # 3) Generic custom / science / audio / 3D model (uses prepare_custom_payload)
                else:
                    payload = {
                        k: v for k, v in item_params.items() if k not in TASK_INTERNAL_PARAM_KEYS
                    }
                    imap = card.get("input_map") or {}
                    if item_kind == "single_file":
                        fpath = in_dir / str(item["file"])
                        ext = fpath.suffix.lower()
                        if ext == ".json":
                            f_obj = json.loads(fpath.read_text(encoding="utf-8"))
                            if isinstance(f_obj, dict):
                                for fk, fv in f_obj.items():
                                    payload.setdefault(fk, fv)
                            else:
                                payload["input"] = f_obj
                        elif ext in (".txt", ".pdb", ".sdf", ".fasta", ".smi"):
                            txt_val = fpath.read_text(encoding="utf-8", errors="replace")
                            if "pdb" in imap:
                                payload.setdefault("pdb", txt_val)
                            elif "sequence" in imap:
                                payload.setdefault("sequence", txt_val.strip())
                            elif "text" in imap:
                                payload.setdefault("text", txt_val)
                            else:
                                payload.setdefault("input_text", txt_val)
                        else:
                            b64 = base64.b64encode(fpath.read_bytes()).decode("ascii")
                            if "audio" in imap or "audio_base64" in imap:
                                payload.setdefault("audio", b64)
                            elif "image" in imap or "image_base64" in imap or "image_b64" in imap:
                                payload.setdefault("image", b64)
                            else:
                                payload.setdefault("file_base64", b64)
                                payload.setdefault("filename", fpath.name)
                    elif item_kind == "bundle_files":
                        b64_list = [
                            base64.b64encode((in_dir / str(fn)).read_bytes()).decode("ascii")
                            for fn in (item.get("files") or [])
                        ]
                        if "images" in imap:
                            payload["images"] = b64_list
                        else:
                            payload["files_base64"] = b64_list

                    upstream_path = str(routing.get("upstream_path") or endpoints.get("primary") or "/v1/predict")
                    if upstream_path == "/v1/tasks":
                        upstream_path = "/v1/predict"
                    if routing.get("strip_v1_prefix") and upstream_path.startswith("/v1/"):
                        upstream_path = upstream_path[3:]
                    forwarded = prepare_custom_payload(payload, card)
                    target_url = f"{predictor_base_url.rstrip('/')}{upstream_path}"
                    status_code, resp_json, raw_text = await _post_predictor_json(
                        http_client, target_url, forwarded, host_header=host_hdr, timeout_s=timeout_s
                    )
                    if status_code >= 400 or resp_json is None:
                        raise RuntimeError(f"Upstream HTTP {status_code}: {raw_text[:1000]}")

                    json_name = f"{stem}.json"
                    (out_dir / json_name).write_text(json.dumps(resp_json, indent=2), encoding="utf-8")
                    _record_output_file(json_name)

                    if isinstance(resp_json, dict):
                        for bkey, ext_out in (
                            ("audio_base64", ".wav"),
                            ("wav_base64", ".wav"),
                            ("mesh_base64", ".glb"),
                            ("glb_base64", ".glb"),
                            ("image_base64", ".png"),
                            ("b64_json", ".png"),
                        ):
                            if isinstance(resp_json.get(bkey), str) and resp_json[bkey]:
                                bin_name = f"{stem}{ext_out}"
                                (out_dir / bin_name).write_bytes(base64.b64decode(resp_json[bkey]))
                                _record_output_file(bin_name)

                    _checkpoint_unit(time.monotonic() - t0, failed=False)

            except Exception as e:
                tb = traceback.format_exc()
                err = store.append_error_log(
                    key_hash,
                    task_id,
                    item=item_name,
                    stage="process_item",
                    message=str(e),
                    exc_tb=tb,
                )
                manifest["errors"].append(err)
                _checkpoint_unit(time.monotonic() - t0, failed=True)
                if not continue_on_error:
                    break

    manifest["current_item"] = None
    manifest["eta_seconds"] = 0.0
    if manifest.get("status") != "cancelled":
        if int(manifest.get("completed_units") or 0) == 0 and int(manifest.get("failed_units") or 0) > 0:
            manifest["status"] = "failed"
        else:
            manifest["status"] = "completed"

    now_dt = _utc_now()
    manifest["completed_at"] = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    ret_hours = int(manifest.get("retention_hours") or 24)
    manifest["expires_at"] = (now_dt + timedelta(hours=ret_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest["error_count"] = len(manifest.get("errors") or [])
    manifest["last_error"] = manifest["errors"][-1] if manifest.get("errors") else None
    store.save_manifest(key_hash, task_id, manifest)
    build_result_zip(store, key_hash, task_id)

    if manifest.get("notify_email"):
        manifest["email_sent"] = send_task_completion_email(manifest)
        store.save_manifest(key_hash, task_id, manifest)

    return manifest


# ---------------------------------------------------------------------------
# Background worker loop & 24h retention reaper
# ---------------------------------------------------------------------------
async def task_worker_loop(
    store: TaskStore,
    get_runtime_hooks: Callable[[], dict[str, Any]],
    stop_event: asyncio.Event | None = None,
) -> None:
    """Continuously dequeue and execute tasks sequentially 1-by-1."""
    store.ensure_dirs()
    try:
        rec = await store.recover_pending_tasks()
        if rec:
            log.info(f"Recovered {rec} pending task(s) on worker startup")
    except Exception as e:
        log.warning(f"Task recovery scan warning: {e}")

    while not (stop_event and stop_event.is_set()):
        try:
            item = await store.dequeue(timeout=1.0)
            if not item:
                continue
            key_hash, task_id = item
            hooks = get_runtime_hooks()
            await execute_task(store, key_hash, task_id, hooks)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f"Task worker loop error: {e}\n{traceback.format_exc()}")
            await asyncio.sleep(1.0)


async def task_reaper_loop(
    store: TaskStore,
    interval_seconds: float = 900.0,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Reap expired terminal tasks (24h post-completion) every 15 minutes."""
    while not (stop_event and stop_event.is_set()):
        try:
            reaped = store.reap_expired()
            if reaped:
                log.info(f"Reaped {len(reaped)} expired task(s): {reaped}")
        except Exception as e:
            log.warning(f"Task reaper error: {e}")
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break


# ---------------------------------------------------------------------------
# Zero-mount proxy support (for model-gateway without /tasks PVC mounted)
# ---------------------------------------------------------------------------
def should_proxy_to_worker(store: TaskStore) -> bool:
    """Return True when this pod should proxy /v1/tasks storage/queue ops to aleph-task-worker."""
    mode = (os.environ.get("TASK_STORAGE_MODE") or "auto").strip().lower()
    if mode == "local" or os.environ.get("TASK_WORKER_LOCAL") == "1":
        return False
    if mode == "proxy":
        return True
    bdir = str(store.base_dir)
    if bdir != DEFAULT_TASKS_DIR:
        return False
    if os.path.ismount(bdir) or os.path.isdir(os.path.join(bdir, "_index")):
        return False
    return True


async def proxy_to_task_worker(request: Request, http_client: httpx.AsyncClient | None = None) -> Response:
    worker_url = (os.environ.get("TASK_WORKER_URL") or DEFAULT_TASK_WORKER_URL).rstrip("/")
    key_hash, owner = extract_caller_identity(request)
    qs = f"?{request.url.query}" if request.url.query else ""
    target = f"{worker_url}{request.url.path}{qs}"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }
    headers["x-tyk-key-hash"] = key_hash
    headers["x-owner"] = owner
    body = await request.body()
    try:
        if http_client is not None:
            resp = await http_client.request(request.method, target, content=body, headers=headers, timeout=120.0)
        else:
            async with httpx.AsyncClient(timeout=120.0) as c:
                resp = await c.request(request.method, target, content=body, headers=headers)
    except Exception as e:
        raise HTTPException(
            503,
            detail={
                "error": {
                    "message": f"Task worker service ({worker_url}) is currently unreachable: {e}",
                    "type": "service_unavailable",
                }
            },
        )
    resp_headers = {
        k: v
        for k, v in resp.headers.items()
        if k.lower() not in ("content-length", "transfer-encoding", "content-encoding", "connection")
    }
    return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers, media_type=resp.headers.get("content-type"))


# ---------------------------------------------------------------------------
# FastAPI Router for /v1/tasks*
# ---------------------------------------------------------------------------
def create_tasks_router(
    store: TaskStore,
    get_runtime_hooks: Callable[[], dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    def _require_owned_manifest(request: Request, task_id: str) -> tuple[str, dict[str, Any]]:
        key_hash, _ = extract_caller_identity(request)
        m = store.load_manifest(key_hash, task_id)
        if m:
            return key_hash, m
        resolved = store.resolve_task(task_id)
        if not resolved:
            raise HTTPException(
                404,
                detail={"error": {"message": f"Task '{task_id}' not found or expired.", "type": "not_found_error"}},
            )
        owner_kh, other_m = resolved
        if owner_kh != key_hash:
            raise HTTPException(
                404,
                detail={"error": {"message": f"Task '{task_id}' not found for this API key.", "type": "not_found_error"}},
            )
        return owner_kh, other_m

    @router.get("/v1/tasks/models")
    async def list_task_models(request: Request, all: bool = False):
        hooks = get_runtime_hooks()
        cards: dict[str, dict] = hooks["model_cards"]()
        model_entry_fn: Callable[[dict], dict] = hooks["model_entry"]
        data = []
        for mid, card in sorted(cards.items()):
            mode = card_mode(card)
            if not all and mode not in ("task", "both"):
                continue
            data.append(model_entry_fn(card))
        return {"object": "list", "data": data}

    @router.get("/v1/tasks/models/{model_id}")
    async def get_task_model_detail(model_id: str):
        hooks = get_runtime_hooks()
        cards: dict[str, dict] = hooks["model_cards"]()
        card = cards.get(model_id)
        if not card:
            raise HTTPException(
                404,
                detail={"error": {"message": f"Unknown model '{model_id}'.", "type": "model_not_found"}},
            )
        model_entry_fn: Callable[[dict], dict] = hooks["model_entry"]
        return model_entry_fn(card)

    @router.post("/v1/tasks", status_code=202)
    async def submit_task(request: Request):
        hooks = get_runtime_hooks()
        if should_proxy_to_worker(store):
            return await proxy_to_task_worker(request, hooks.get("http_client"))
        key_hash, manifest = await stage_task_submission(request, store, hooks["model_cards"]())
        if hooks.get("inline_execution"):
            await execute_task(store, key_hash, manifest["task_id"], hooks)
            manifest = store.load_manifest(key_hash, manifest["task_id"]) or manifest
        return JSONResponse(status_code=202, content=store.public_manifest_view(manifest))

    @router.get("/v1/tasks")
    async def list_tasks(request: Request, status: str | None = None, limit: int = 50):
        hooks = get_runtime_hooks()
        if should_proxy_to_worker(store):
            return await proxy_to_task_worker(request, hooks.get("http_client"))
        key_hash, _ = extract_caller_identity(request)
        items = store.list_tasks(key_hash, status_filter=status, limit=limit)
        return {"object": "list", "data": items}

    @router.get("/v1/tasks/{task_id}")
    async def get_task_status(task_id: str, request: Request):
        hooks = get_runtime_hooks()
        if should_proxy_to_worker(store):
            return await proxy_to_task_worker(request, hooks.get("http_client"))
        _, manifest = _require_owned_manifest(request, task_id)
        return store.public_manifest_view(manifest)

    @router.get("/v1/tasks/{task_id}/error.log")
    async def get_task_error_log(task_id: str, request: Request, tail: int | None = None):
        hooks = get_runtime_hooks()
        if should_proxy_to_worker(store):
            return await proxy_to_task_worker(request, hooks.get("http_client"))
        key_hash, _ = _require_owned_manifest(request, task_id)
        content = store.read_error_log(key_hash, task_id, tail_lines=tail)
        return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")

    @router.get("/v1/tasks/{task_id}/result")
    async def download_task_result(task_id: str, request: Request):
        hooks = get_runtime_hooks()
        if should_proxy_to_worker(store):
            return await proxy_to_task_worker(request, hooks.get("http_client"))
        key_hash, manifest = _require_owned_manifest(request, task_id)
        if manifest.get("status") not in ("completed", "failed", "cancelled"):
            raise HTTPException(
                409,
                detail={
                    "error": {
                        "message": f"Task '{task_id}' is still {manifest.get('status')} ({manifest.get('completed_units', 0)}/{manifest.get('total_units', 0)} {manifest.get('unit', 'units')}). Poll GET /v1/tasks/{task_id} or download finished files via GET /v1/tasks/{task_id}/files/out/<filename>.",
                        "type": "task_not_ready",
                    }
                },
            )
        zpath = store.result_zip_path(key_hash, task_id)
        if not zpath.is_file():
            zpath = build_result_zip(store, key_hash, task_id)
        return FileResponse(
            path=str(zpath),
            media_type="application/zip",
            filename=f"{task_id}.zip",
        )

    @router.get("/v1/tasks/{task_id}/files/out/{filename:path}")
    async def download_task_output_file(task_id: str, filename: str, request: Request):
        hooks = get_runtime_hooks()
        if should_proxy_to_worker(store):
            return await proxy_to_task_worker(request, hooks.get("http_client"))
        key_hash, _ = _require_owned_manifest(request, task_id)
        safe_fn = _safe_filename(filename, default="")
        if not safe_fn:
            raise HTTPException(404, detail={"error": {"message": "Output file not found", "type": "not_found_error"}})
        out_dir = store.task_dir(key_hash, task_id) / "out"
        fpath = (out_dir / safe_fn).resolve()
        if not str(fpath).startswith(str(out_dir.resolve()) + os.sep) or not fpath.is_file():
            raise HTTPException(404, detail={"error": {"message": f"Output file '{safe_fn}' not found", "type": "not_found_error"}})
        return FileResponse(path=str(fpath), filename=safe_fn)

    @router.delete("/v1/tasks/{task_id}")
    async def cancel_or_delete_task(task_id: str, request: Request):
        hooks = get_runtime_hooks()
        if should_proxy_to_worker(store):
            return await proxy_to_task_worker(request, hooks.get("http_client"))
        key_hash, manifest = _require_owned_manifest(request, task_id)
        status = manifest.get("status")
        if status in ACTIVE_TASK_STATUSES:
            manifest["status"] = "cancelled"
            now_dt = _utc_now()
            manifest["completed_at"] = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            ret_hours = int(manifest.get("retention_hours") or 24)
            manifest["expires_at"] = (now_dt + timedelta(hours=ret_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
            store.save_manifest(key_hash, task_id, manifest)
            return store.public_manifest_view(manifest)
        store.delete_task_files(key_hash, task_id)
        return {"task_id": task_id, "object": "task", "deleted": True}

    return router
