"""
Card-driven model inference gateway (HAMi / KServe / Knative).

Design: docs/GATEWAY-ARCHITECTURE.md. Models declare themselves via `details.yaml`
ConfigMaps (label `model-details=true`). The gateway reads these cards, merges
live state from InferenceServices, and routes requests to model pods through the
knative-local-gateway. No model names are hardcoded.

Phase 1 scope: discovery (cards + ISVC watch), /v1/models, embeddings + chat
handlers, /v1/{custom} forward catch-all, /healthz /readyz /metrics.
"""
from __future__ import annotations

import asyncio
import html
import json
import os
import threading
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from kubernetes import client, config, watch

import usage

# ── Anthropic Messages API <-> OpenAI Chat Completions translation ──────────────
# Converts an Anthropic /v1/messages request into an OpenAI chat-completions body,
# runs it through the normal chat pipeline, then converts the OpenAI response (and
# SSE stream) back to Anthropic shape. Common core only — unsupported Anthropic
# fields are dropped on input.


def _anth_flatten_text(content: Any) -> str:
    """Anthropic `system` / simple content -> a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
        return "\n".join(parts)
    return ""


def _anth_convert_user_content(content: Any) -> Any:
    """Anthropic message content -> OpenAI content (string, or multimodal array)."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    has_media = any(
        isinstance(b, dict) and b.get("type") in ("image", "tool_result", "tool_use")
        for b in content
    )
    if not has_media:
        return _anth_flatten_text(content)
    out: list[dict] = []
    for b in content:
        if not isinstance(b, dict):
            continue
        btype = b.get("type")
        if btype == "text":
            out.append({"type": "text", "text": b.get("text", "")})
        elif btype == "image":
            src = b.get("source", {}) or {}
            if src.get("type") == "base64":
                url = f"data:{src.get('media_type','image/png')};base64,{src.get('data','')}"
            else:
                url = src.get("url", "")
            out.append({"type": "image_url", "image_url": {"url": url}})
        elif btype == "tool_result":
            out.append({"type": "text", "text": _anth_flatten_text(b.get("content"))})
    return out or _anth_flatten_text(content)


def anth_to_openai(body: dict) -> dict:
    """Convert an Anthropic /v1/messages request body to OpenAI chat-completions."""
    out: dict[str, Any] = {"model": body.get("model")}

    if body.get("max_tokens") is not None:
        out["max_tokens"] = body["max_tokens"]

    messages: list[dict] = []
    system = body.get("system")
    if system:
        messages.append({"role": "system", "content": _anth_flatten_text(system)})
    for m in body.get("messages", []) or []:
        role = m.get("role", "user")
        messages.append({"role": role, "content": _anth_convert_user_content(m.get("content"))})
    out["messages"] = messages

    for a_key, o_key in (("temperature", "temperature"), ("top_p", "top_p"),
                         ("top_k", "top_k"), ("stream", "stream")):
        if body.get(a_key) is not None:
            out[o_key] = body[a_key]
    if body.get("stop_sequences"):
        out["stop"] = body["stop_sequences"]

    # Tools: Anthropic {name, description, input_schema} -> OpenAI function tools.
    if body.get("tools"):
        tools = []
        for t in body["tools"]:
            if not isinstance(t, dict) or "name" not in t:
                continue
            tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object"}),
                },
            })
        if tools:
            out["tools"] = tools

    # tool_choice: Anthropic {type: auto|any|tool|none} -> OpenAI form.
    tc = body.get("tool_choice")
    if isinstance(tc, dict):
        ttype = tc.get("type")
        if ttype == "auto":
            out["tool_choice"] = "auto"
        elif ttype == "any":
            out["tool_choice"] = "required"
        elif ttype == "none":
            out["tool_choice"] = "none"
        elif ttype == "tool" and tc.get("name"):
            out["tool_choice"] = {"type": "function", "function": {"name": tc["name"]}}
    return out


def anth_desired_thinking(body: dict) -> tuple[bool, str | None, int | None]:
    """Extract raw Anthropic thinking hints — no per-model effort mapping.

    Returns (enabled, raw_effort, budget_tokens). Effort strings are passed through
    as sent by the client; the model card's effort_aliases / effort_map resolve them.
    """
    oc = body.get("output_config") or {}
    if oc.get("effort") is not None:
        return True, str(oc["effort"]).lower(), None

    th = body.get("thinking") or {}
    ttype = th.get("type")
    if ttype == "adaptive":
        return True, None, None
    if ttype == "enabled":
        bt = th.get("budget_tokens")
        if isinstance(bt, int):
            return True, None, bt
        return True, None, None
    if ttype == "disabled":
        return False, None, None
    return False, None, None


# OpenAI -> Anthropic response translation

_ANTH_STOP_MAP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "end_turn",
    None: "end_turn",
}


def anth_from_openai(resp: dict, model: str, *, include_thinking: bool = False) -> dict:
    """Convert an OpenAI chat-completions response to Anthropic Messages shape."""
    choices = resp.get("choices") or [{}]
    choice = choices[0]
    msg = choice.get("message", {}) or {}

    blocks: list[dict] = []
    if include_thinking:
        reasoning = msg.get("reasoning") or msg.get("reasoning_content")
        if reasoning:
            blocks.append({"type": "thinking", "thinking": reasoning})
    text = msg.get("content")
    if text:
        blocks.append({"type": "text", "text": text})
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function", {}) or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except Exception:
            args = {}
        blocks.append({
            "type": "tool_use",
            "id": tc.get("id", "toolu_" + uuid.uuid4().hex[:24]),
            "name": fn.get("name", ""),
            "input": args,
        })
    if not blocks:
        blocks.append({"type": "text", "text": ""})

    usage = resp.get("usage", {}) or {}
    return {
        "id": resp.get("id", "msg_" + uuid.uuid4().hex[:24]),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": blocks,
        "stop_reason": _ANTH_STOP_MAP.get(choice.get("finish_reason"), "end_turn"),
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


# ── Anthropic SSE streaming helpers ────────────────────────────────────────────

def _anth_sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def anth_stream_start_events(model: str) -> list[bytes]:
    msg_id = "msg_" + uuid.uuid4().hex[:24]
    # Only message_start here — content blocks are opened lazily by the
    # streaming generator as text or tool_use deltas arrive, so a tool-only
    # response is not fronted by an empty text block.
    return [
        _anth_sse("message_start", {
            "type": "message_start",
            "message": {
                "id": msg_id, "type": "message", "role": "assistant",
                "model": model, "content": [],
                "stop_reason": None, "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }),
    ]


def anth_stream_stop_events(finish_reason: str | None, output_tokens: int,
                            resources: dict | None = None) -> list[bytes]:
    # The generator closes the last open content block itself; this only emits
    # the trailing message_delta + message_stop.
    delta: dict[str, Any] = {
        "type": "message_delta",
        "delta": {"stop_reason": _ANTH_STOP_MAP.get(finish_reason, "end_turn"),
                  "stop_sequence": None},
        "usage": {"output_tokens": output_tokens},
    }
    if resources:
        delta["resources"] = resources
    return [
        _anth_sse("message_delta", delta),
        _anth_sse("message_stop", {"type": "message_stop"}),
    ]


def anth_parse_openai_sse_line(line: str) -> dict | None:
    """Parse one SSE line from an OpenAI stream into a dict, or None."""
    line = line.strip()
    if not line.startswith("data:"):
        return None
    payload = line[len("data:"):].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None


# ── Config ───────────────────────────────────────────────────────────────────
MODELS_NS = os.environ.get("MODELS_NAMESPACE", "models")
KNATIVE_GW = os.environ.get(
    "KNATIVE_GATEWAY",
    "http://knative-local-gateway.istio-system.svc.cluster.local",
)
CARD_LABEL = os.environ.get("CARD_LABEL_SELECTOR", "model-details=true")
UPSTREAM_TIMEOUT = float(os.environ.get("UPSTREAM_TIMEOUT", "300"))

KSERVE_GROUP = "serving.kserve.io"
KSERVE_VERSION = "v1beta1"
KSERVE_PLURAL = "inferenceservices"

# OpenWebUI meta-task prompt signals (detected to apply meta_tasks defaults).
_OWUI_SIGNALS = {
    "title": "Generate a concise, 3-5 word title",
    "tags": "Generate 1-3 broad tags",
    "followups": "Suggest 3-5 relevant follow-up questions",
}

# ── In-memory state (updated by background watches) ────────────────────────────
# model_id -> card dict (parsed details.json)
CARDS: dict[str, dict] = {}
# isvc_name -> {"ready": bool}
ISVC_STATE: dict[str, dict] = {}
# node name -> {aleph.* label: value} (hardware provenance from node-labeler DS)
NODE_LABELS: dict[str, dict] = {}
# k8s_name (ISVC) -> {predictor pod name -> node name}. Keyed by pod name (not
# just node) so a revision rollout's old-pod DELETE can't clobber the new pod's
# mapping when both land on the same node.
POD_NODE: dict[str, dict[str, str]] = {}
_STATE_LOCK = threading.Lock()

_DISCOVERY = {"cards_seeded": False, "isvc_seeded": False, "last_event": 0.0}

# Prometheus-ish counters (minimal Phase 1 stub).
_METRICS = {"requests_total": 0, "requests_error": 0}

app = FastAPI(title="model-gateway", version="0.1")


# ── K8s clients ────────────────────────────────────────────────────────────────
def _load_kube() -> None:
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def _core() -> "client.CoreV1Api":
    return client.CoreV1Api()


def _custom() -> "client.CustomObjectsApi":
    return client.CustomObjectsApi()


def _apps() -> "client.AppsV1Api":
    return client.AppsV1Api()


# ── Scale-to-zero detection ────────────────────────────────────────────────────
# The ISVC "Ready" condition stays True even when a revision is scaled to zero, so
# readiness alone can't tell us whether a pod exists. We read the live replica
# count of the active predictor revision's Deployment (short TTL cache to avoid
# hammering the apiserver on the request hot path).
_RR_CACHE: dict[str, tuple[float, int]] = {}
_RR_TTL = 3.0


def _ready_replicas_sync(k8s_name: str) -> int:
    """Ready replica count for a model's active predictor revision.

    Returns 0 when scaled to zero, >0 when warm, -1 on error (caller must not
    block requests on an unknown).
    """
    try:
        isvc = _custom().get_namespaced_custom_object(
            KSERVE_GROUP, KSERVE_VERSION, MODELS_NS, KSERVE_PLURAL, k8s_name
        )
        pred = ((isvc.get("status", {}) or {}).get("components", {}) or {}).get(
            "predictor", {}
        ) or {}
        traffic = pred.get("traffic", []) or []
        # Prefer the live-traffic revision, then the last ready one, then the last
        # *created* one. The latestCreatedRevision fallback matters for a brand-new
        # scale-to-zero model that has never been ready yet: Knative has already
        # created its Deployment (at 0 replicas), so we can detect "0" and let the
        # cold-start guard fire a wake-up + 503 instead of fail-open -> Knative 404.
        rev = (
            next(
                (t.get("revisionName") for t in traffic if (t.get("percent") or 0) > 0),
                None,
            )
            or pred.get("latestReadyRevision")
            or pred.get("latestCreatedRevision")
            or ""
        )
        if rev:
            deps = _apps().list_namespaced_deployment(
                MODELS_NS, label_selector=f"serving.knative.dev/revision={rev}"
            )
            if deps.items:
                return deps.items[0].status.ready_replicas or 0
            return 0
        # RawDeployment ISVCs (no Knative revision): read the Deployment directly.
        dep = _apps().read_namespaced_deployment(f"{k8s_name}-predictor", MODELS_NS)
        return dep.status.ready_replicas or 0
    except Exception as e:
        print(f"[SCALE0] ready_replicas {k8s_name}: {e}", flush=True)
        return -1


def _ready_replicas(k8s_name: str) -> int:
    now = time.time()
    ent = _RR_CACHE.get(k8s_name)
    if ent and now - ent[0] < _RR_TTL:
        return ent[1]
    val = _ready_replicas_sync(k8s_name)
    _RR_CACHE[k8s_name] = (now, val)
    return val


async def _wake_up(info: dict) -> None:
    """Nudge Knative's activator to scale a sleeping revision up from zero."""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.get(upstream_url("/v1/models"), headers={"Host": info["host"]})
    except Exception as e:  # expected to time out while the pod boots
        print(f"[SCALE0] wake {info['id']}: {type(e).__name__}", flush=True)


async def cold_start_guard(info: dict):
    """If the model is scaled to zero, fire an async wake-up and return a friendly
    503 telling the caller to retry. Returns None when the model is warm."""
    rr = await asyncio.to_thread(_ready_replicas, info["k8s_name"])
    if rr == 0:
        print(f"[SCALE0] {info['id']} at 0 replicas -> wake + 503", flush=True)
        asyncio.create_task(_wake_up(info))
        est = (info.get("scaling", {}) or {}).get("cold_start_estimate", "2-5 minutes")
        return JSONResponse(
            {
                "error": {
                    "message": (
                        f"Model '{info['id']}' is starting up (scaled to zero for "
                        f"efficiency). Please retry in {est}."
                    ),
                    "type": "model_starting",
                    "code": "model_scaled_to_zero",
                }
            },
            status_code=503,
            headers={"Retry-After": "30"},
        )
    return None


# ── Card parsing ───────────────────────────────────────────────────────────────
def _parse_card(cm: Any) -> dict | None:
    """Extract and parse details.json from a ConfigMap object."""
    data = getattr(cm, "data", None) or {}
    raw = data.get("details.json") or data.get("details.yaml")
    if not raw:
        return None
    try:
        card = json.loads(raw)
    except Exception as e:
        name = getattr(getattr(cm, "metadata", None), "name", "?")
        print(f"[CARD] {name}: invalid JSON: {e}", flush=True)
        return None
    if not card.get("id"):
        return None
    return card


def _ingest_card(cm: Any) -> None:
    card = _parse_card(cm)
    if not card:
        return
    with _STATE_LOCK:
        CARDS[card["id"]] = card
    print(f"[CARD] loaded {card['id']} (type={card.get('type')})", flush=True)


def _remove_card(cm: Any) -> None:
    card = _parse_card(cm)
    if not card:
        return
    with _STATE_LOCK:
        CARDS.pop(card["id"], None)
    print(f"[CARD] removed {card['id']}", flush=True)


def _isvc_ready(isvc: dict) -> bool:
    for c in (isvc.get("status", {}) or {}).get("conditions", []) or []:
        if c.get("type") == "Ready":
            return c.get("status") == "True"
    return False


def _parse_cpu(v: Any) -> float | None:
    """K8s CPU quantity -> cores. '4' -> 4.0, '500m' -> 0.5."""
    try:
        s = str(v)
        if s.endswith("m"):
            return round(int(s[:-1]) / 1000, 3)
        return float(s)
    except Exception:
        return None


_MEM_UNITS = {
    "Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024,
    "K": 1000 / 1024 / 1024, "M": 1000 * 1000 / 1024 / 1024,
    "G": 1000 ** 3 / 1024 / 1024, "T": 1000 ** 4 / 1024 / 1024,
}


def _parse_mem_mib(v: Any) -> int | None:
    """K8s memory quantity -> MiB. '16Gi' -> 16384, '512Mi' -> 512."""
    try:
        s = str(v).strip()
        for unit, factor in _MEM_UNITS.items():
            if s.endswith(unit):
                return int(float(s[: -len(unit)]) * factor)
        return int(int(s) / 1024 / 1024)  # bare bytes
    except Exception:
        return None


def _extract_resources(isvc: dict) -> dict:
    """Pull the model's allocated compute from the ISVC predictor spec."""
    pred = (isvc.get("spec", {}) or {}).get("predictor", {}) or {}
    containers = pred.get("containers") or []
    c = next((x for x in containers if x.get("name") == "kserve-container"), None)
    if c is None and containers:
        c = containers[0]
    if not c:
        return {}
    res = c.get("resources", {}) or {}
    lim, req = res.get("limits", {}) or {}, res.get("requests", {}) or {}
    get = lambda k: lim.get(k) if lim.get(k) is not None else req.get(k)

    out: dict[str, Any] = {}
    gpu = get("nvidia.com/gpu")
    if gpu is not None:
        try:
            out["gpus"] = int(gpu)
        except Exception:
            pass
    vram = get("nvidia.com/gpumem")
    if vram is not None:
        try:
            out["vram_mib"] = int(vram)
        except Exception:
            pass
    cpu = get("cpu")
    if cpu is not None:
        cores = _parse_cpu(cpu)
        if cores is not None:
            out["cpu_cores"] = cores
    mem = get("memory")
    if mem is not None:
        ram = _parse_mem_mib(mem)
        if ram is not None:
            out["system_ram_mib"] = ram
    return out


def _ingest_isvc(isvc: dict) -> None:
    name = isvc.get("metadata", {}).get("name")
    if not name:
        return
    with _STATE_LOCK:
        ISVC_STATE[name] = {
            "ready": _isvc_ready(isvc),
            "resources": _extract_resources(isvc),
        }


def _remove_isvc(isvc: dict) -> None:
    name = isvc.get("metadata", {}).get("name")
    if not name:
        return
    with _STATE_LOCK:
        ISVC_STATE.pop(name, None)


# ── Node hardware provenance (labels from the node-labeler DaemonSet) ───────────
def _aleph_labels(labels: dict | None) -> dict:
    """Keep only the aleph.* hardware labels (gpu/cpu/node provenance)."""
    return {k: v for k, v in (labels or {}).items() if k.startswith("aleph.")}


def _ingest_node(node: Any) -> None:
    meta = getattr(node, "metadata", None)
    name = getattr(meta, "name", None)
    if not name:
        return
    with _STATE_LOCK:
        NODE_LABELS[name] = _aleph_labels(getattr(meta, "labels", None))


def _remove_node(node: Any) -> None:
    name = getattr(getattr(node, "metadata", None), "name", None)
    if name:
        with _STATE_LOCK:
            NODE_LABELS.pop(name, None)


def _ingest_pod(pod: Any) -> None:
    """Track which node each predictor pod of a model landed on."""
    meta = getattr(pod, "metadata", None)
    spec = getattr(pod, "spec", None)
    status = getattr(pod, "status", None)
    name = getattr(meta, "name", None)
    labels = getattr(meta, "labels", None) or {}
    isvc = labels.get("serving.kserve.io/inferenceservice")
    node = getattr(spec, "node_name", None)
    phase = getattr(status, "phase", None)
    if not isvc or not name:
        return
    with _STATE_LOCK:
        pods = POD_NODE.setdefault(isvc, {})
        if node and phase in ("Running", "Pending"):
            pods[name] = node
        else:
            # Unscheduled / terminating / succeeded-failed: drop this pod.
            pods.pop(name, None)
            if not pods:
                POD_NODE.pop(isvc, None)


def _remove_pod(pod: Any) -> None:
    meta = getattr(pod, "metadata", None)
    name = getattr(meta, "name", None)
    labels = getattr(meta, "labels", None) or {}
    isvc = labels.get("serving.kserve.io/inferenceservice")
    if not isvc or not name:
        return
    with _STATE_LOCK:
        pods = POD_NODE.get(isvc)
        if pods is not None:
            pods.pop(name, None)
            if not pods:
                POD_NODE.pop(isvc, None)


def _node_for(k8s_name: str) -> str | None:
    """Best node for a model: any currently tracked (running/pending) pod's node."""
    pods = POD_NODE.get(k8s_name) or {}
    return next(iter(pods.values()), None)


# ── Discovery: initial seed + background watches ───────────────────────────────
def seed_cards() -> None:
    try:
        cms = _core().list_namespaced_config_map(
            MODELS_NS, label_selector=CARD_LABEL
        )
        for cm in cms.items:
            _ingest_card(cm)
        _DISCOVERY["cards_seeded"] = True
        print(f"[DISCOVERY] seeded {len(CARDS)} card(s)", flush=True)
    except Exception as e:
        print(f"[DISCOVERY] card seed error: {e}", flush=True)


def seed_isvcs() -> None:
    try:
        resp = _custom().list_namespaced_custom_object(
            KSERVE_GROUP, KSERVE_VERSION, MODELS_NS, KSERVE_PLURAL
        )
        for isvc in resp.get("items", []):
            _ingest_isvc(isvc)
        _DISCOVERY["isvc_seeded"] = True
        print(f"[DISCOVERY] seeded {len(ISVC_STATE)} ISVC(s)", flush=True)
    except Exception as e:
        print(f"[DISCOVERY] isvc seed error: {e}", flush=True)


def watch_cards() -> None:
    while True:
        try:
            w = watch.Watch()
            for event in w.stream(
                _core().list_namespaced_config_map,
                MODELS_NS,
                label_selector=CARD_LABEL,
                timeout_seconds=300,
            ):
                _DISCOVERY["last_event"] = time.time()
                etype = event["type"]
                if etype in ("ADDED", "MODIFIED"):
                    _ingest_card(event["object"])
                elif etype == "DELETED":
                    _remove_card(event["object"])
        except Exception as e:
            print(f"[WATCH cards] reconnect after error: {e}", flush=True)
            time.sleep(2)


def watch_isvcs() -> None:
    while True:
        try:
            w = watch.Watch()
            for event in w.stream(
                _custom().list_namespaced_custom_object,
                KSERVE_GROUP,
                KSERVE_VERSION,
                MODELS_NS,
                KSERVE_PLURAL,
                timeout_seconds=300,
            ):
                _DISCOVERY["last_event"] = time.time()
                etype = event["type"]
                if etype in ("ADDED", "MODIFIED"):
                    _ingest_isvc(event["object"])
                elif etype == "DELETED":
                    _remove_isvc(event["object"])
        except Exception as e:
            print(f"[WATCH isvc] reconnect after error: {e}", flush=True)
            time.sleep(2)


def seed_nodes() -> None:
    try:
        for n in _core().list_node().items:
            _ingest_node(n)
        print(f"[DISCOVERY] seeded {len(NODE_LABELS)} node(s)", flush=True)
    except Exception as e:
        print(f"[DISCOVERY] node seed error: {e}", flush=True)


def seed_pods() -> None:
    try:
        pods = _core().list_namespaced_pod(
            MODELS_NS, label_selector="serving.kserve.io/inferenceservice"
        )
        for p in pods.items:
            _ingest_pod(p)
        print(f"[DISCOVERY] seeded {len(POD_NODE)} predictor pod->node map(s)", flush=True)
    except Exception as e:
        print(f"[DISCOVERY] pod seed error: {e}", flush=True)


def watch_nodes() -> None:
    while True:
        try:
            w = watch.Watch()
            for event in w.stream(_core().list_node, timeout_seconds=300):
                etype = event["type"]
                if etype in ("ADDED", "MODIFIED"):
                    _ingest_node(event["object"])
                elif etype == "DELETED":
                    _remove_node(event["object"])
        except Exception as e:
            print(f"[WATCH nodes] reconnect after error: {e}", flush=True)
            time.sleep(2)


def watch_pods() -> None:
    while True:
        try:
            w = watch.Watch()
            for event in w.stream(
                _core().list_namespaced_pod,
                MODELS_NS,
                label_selector="serving.kserve.io/inferenceservice",
                timeout_seconds=300,
            ):
                etype = event["type"]
                if etype in ("ADDED", "MODIFIED"):
                    _ingest_pod(event["object"])
                elif etype == "DELETED":
                    _remove_pod(event["object"])
        except Exception as e:
            print(f"[WATCH pods] reconnect after error: {e}", flush=True)
            time.sleep(2)


@app.on_event("startup")
async def _startup() -> None:
    _load_kube()
    seed_cards()
    seed_isvcs()
    seed_nodes()
    seed_pods()
    threading.Thread(target=watch_cards, daemon=True).start()
    threading.Thread(target=watch_isvcs, daemon=True).start()
    threading.Thread(target=watch_nodes, daemon=True).start()
    threading.Thread(target=watch_pods, daemon=True).start()
    print("[STARTUP] discovery running", flush=True)


# ── Routing helpers ────────────────────────────────────────────────────────────
def resolve(model_id: str) -> dict | None:
    """Return merged routing info for a model, or None if unknown."""
    with _STATE_LOCK:
        card = CARDS.get(model_id)
        if not card:
            return None
        routing = card.get("routing", {}) or {}
        k8s_name = routing.get("k8s_name") or model_id
        isvc = ISVC_STATE.get(k8s_name, {})
        return {
            "id": model_id,
            "card": card,
            "type": card.get("type", "chat"),
            "k8s_name": k8s_name,
            "host": f"{k8s_name}-predictor.{MODELS_NS}.svc.cluster.local",
            "ready": isvc.get("ready", False),
            "resources": isvc.get("resources", {}) or {},
            "upstream_model_id": routing.get("upstream_model_id"),
            "no_stream": routing.get("no_stream", False),
            "scaling": card.get("scaling", {}) or {},
        }


def resource_block(info: dict, latency_ms: int) -> dict:
    """Compute/footprint block attached to responses (alloc + measured time).

    NOTE: gpus/vram/cpu/ram are the *allocated* footprint from the ISVC spec.
    Live GPU utilization (% / instantaneous VRAM) needs a metrics source
    (DCGM / HAMi exporter) and is not wired yet — see docs/GATEWAY-ARCHITECTURE.md.
    """
    block = {"model": info["id"]}
    block.update(info.get("resources", {}) or {})
    with _STATE_LOCK:
        node = _node_for(info["k8s_name"])
        labels = NODE_LABELS.get(node, {}) if node else {}
    if node:
        block["node"] = node
        gpu_product = labels.get("aleph.gpu/product")
        if gpu_product:
            block["gpu_product"] = gpu_product
    block["latency_ms"] = latency_ms
    return block


def _identity(request: Request) -> tuple[str, str, str | None]:
    """Resolve caller identity from Tyk-injected headers.

    Tyk validates the API key and forwards the key's metadata as headers
    (X-Aleph-Identity = service/ldap name, X-Aleph-Account = billing bucket,
    X-Aleph-Identity-Type = service|user). Calls that reach the gateway without
    going through Tyk (e.g. in-cluster debugging) are logged as 'anonymous'.
    """
    h = request.headers
    ident = h.get("x-aleph-identity")
    acct = h.get("x-aleph-account")
    itype = h.get("x-aleph-identity-type") or ("service" if ident else "anonymous")
    return (ident or "anonymous", itype, acct)


def _limits(info: dict) -> tuple[int, int]:
    """(context_window, max_completion_tokens) declared in the model card."""
    lim = (info.get("card", {}) or {}).get("limits", {}) or {}
    def _i(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0
    return _i(lim.get("context_window")), _i(lim.get("max_completion_tokens"))


def _log_usage(request: Request, info: dict, *, endpoint: str, api: str,
               status: int, latency_ms: int, usage_obj: dict | None = None,
               cold_start: bool = False, stream: bool = False,
               request_id: str | None = None) -> None:
    """Write one accounting record for a served (or cold-started) request."""
    ident, itype, acct = _identity(request)
    cw, mct = _limits(info)
    usage.record(
        identity=ident, identity_type=itype, account=acct,
        endpoint=endpoint, api=api, model=info.get("id", "unknown"),
        status=status, latency_ms=latency_ms, usage=usage_obj,
        resources=resource_block(info, latency_ms),
        context_window=cw, max_completion_tokens=mct,
        cold_start=cold_start, stream=stream, request_id=request_id,
    )


async def _guard_cold(request: Request, info: dict, endpoint: str, api: str):
    """cold_start_guard + log the scale-from-zero event (it has real GPU cost)."""
    cold = await cold_start_guard(info)
    if cold is not None:
        _log_usage(request, info, endpoint=endpoint, api=api, status=503,
                   latency_ms=0, cold_start=True)
    return cold


def upstream_url(path: str) -> str:
    path = path if path.startswith("/") else f"/{path}"
    return f"{KNATIVE_GW}{path}"


def upstream_headers(info: dict, content_type: str = "application/json") -> dict:
    return {"Content-Type": content_type, "Host": info["host"]}


def apply_defaults(card: dict, body: dict) -> dict:
    """Fill in card defaults for fields the client didn't set."""
    defaults = (card.get("defaults", {}) or {}).get("chat", {}) or {}
    for k, v in defaults.items():
        if k == "thinking":
            continue
        if k not in body or body[k] is None:
            body[k] = v
    return body


def _msg_text(content) -> str:
    """Flatten an OpenAI message content (str or list of typed blocks) to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def detect_meta_task(body: dict) -> str | None:
    """Detect an OpenWebUI meta-task (title/tags/followups) by its signature prompt.
    OpenWebUI sends these as a one-off generation, but the task text may arrive as a
    single user message OR split across system+user (and the content may be a typed
    block list), so scan every message rather than only a lone user message."""
    for msg in (body.get("messages") or []):
        text = _msg_text(msg.get("content"))
        if not text:
            continue
        for task, signal in _OWUI_SIGNALS.items():
            if signal in text:
                return task
    return None


def _raw_effort(v) -> str | None:
    """Pull effort string from OpenAI reasoning_effort (str or {effort:...} object)."""
    if v is None:
        return None
    if isinstance(v, dict):
        v = v.get("effort")
    return str(v).lower() if v is not None else None


def resolve_effort(card: dict, raw: str | None) -> str | None:
    """Map a client effort token to a card effort_map key via card effort_aliases."""
    if raw is None:
        return None
    pt = (card.get("param_translation", {}) or {}).get("thinking", {}) or {}
    key = str(raw).lower()
    aliases = pt.get("effort_aliases") or {}
    if key in aliases:
        return aliases[key]
    effort_map = pt.get("effort_map") or {}
    if key in effort_map:
        return key
    return pt.get("default_effort")


def _effort_budget(pt: dict, effort: str) -> int | None:
    """Look up thinking_token_budget for an effort level (None = uncapped)."""
    entry = (pt.get("effort_map", {}) or {}).get(effort)
    if entry is None:
        entry = (pt.get("effort_map", {}) or {}).get("medium")
    if entry is None:
        return None
    if isinstance(entry, dict):
        return entry.get("thinking_token_budget")
    if isinstance(entry, int):
        return entry
    return None


def apply_thinking(
    card: dict,
    body: dict,
    enabled: bool,
    *,
    effort: str | None = None,
    budget_tokens: int | None = None,
) -> dict:
    """Translate a desired thinking on/off into the model's dialect via the card."""
    pt = (card.get("param_translation", {}) or {}).get("thinking", {}) or {}
    mode = pt.get("mode", "none")
    if mode in ("none", "always_on"):
        return body
    if mode == "budget":
        answer_reserve = pt.get("answer_reserve", 512)
        if not enabled:
            effort = pt.get("disabled_effort", "none")
        if budget_tokens is not None:
            body["thinking_token_budget"] = budget_tokens
        else:
            if effort is None:
                chat_def = (card.get("defaults", {}) or {}).get("chat", {}) or {}
                effort = (chat_def.get("thinking", {}) or {}).get("effort", "medium")
            budget = _effort_budget(pt, effort)
            if budget is not None:
                body["thinking_token_budget"] = budget
        budget = body.get("thinking_token_budget")
        # Budget 0 forces immediate Solution; don't inflate max_tokens for meta caps.
        if isinstance(budget, int) and budget > 0:
            cap = (card.get("limits", {}) or {}).get("max_completion_tokens")
            floor = budget + answer_reserve
            mt = body.get("max_tokens")
            if not isinstance(mt, int) or mt < floor:
                body["max_tokens"] = min(floor, cap) if isinstance(cap, int) and cap > 0 else floor
        return body
    if mode == "toggle":
        inject = pt.get("on" if enabled else "off", {}) or {}
        body.update(inject)
    elif mode == "effort":
        # reasoning_effort is a direct passthrough param. When thinking is enabled,
        # only supply the card's default if the client didn't set it (respect the
        # caller's chosen effort). When disabled (e.g. meta-tasks), force "off".
        if enabled:
            for k, v in (pt.get("on", {}) or {}).items():
                body.setdefault(k, v)
        else:
            body.update(pt.get("off", {}) or {})
    return body


def prepare_chat(
    info: dict,
    body: dict,
    *,
    think_enabled: bool | None = None,
    think_effort: str | None = None,
    think_budget: int | None = None,
) -> tuple[dict, bool]:
    card = info["card"]
    pt = (card.get("param_translation", {}) or {}).get("thinking", {}) or {}
    pt_mode = pt.get("mode", "none")
    body = apply_defaults(card, body)

    # Detect an explicit client "off" (OpenAI reasoning_effort none/disabled/off). gpt-oss
    # always reasons internally, but the client asked for no reasoning -- treat as off so we
    # strip the (minimal) reasoning and cap tokens. The model still runs at low effort upstream.
    _OFF_EFFORTS = {"none", "disabled", "off"}
    _re = _raw_effort(body.get("reasoning_effort")) if body.get("reasoning_effort") is not None else None
    client_off = isinstance(_re, str) and _re.lower() in _OFF_EFFORTS

    meta = detect_meta_task(body)
    thinking_enabled = True
    chat_defaults = (card.get("defaults", {}) or {}).get("chat", {}) or {}
    thinking_enabled = (chat_defaults.get("thinking", {}) or {}).get("enabled", True)
    if client_off:
        thinking_enabled = False
    meta_effort = None

    if meta:
        meta_cfg = ((card.get("defaults", {}) or {}).get("meta_tasks", {}) or {}).get(meta, {})
        if "max_tokens" in meta_cfg:
            cur = body.get("max_tokens")
            cap = meta_cfg["max_tokens"]
            if (card.get("behavior", {}) or {}).get("reasoning_model"):
                # Always-reasoning models (gpt-oss) spend a VARIABLE number of tokens on
                # internal reasoning before the final answer, so a small client budget
                # (OpenWebUI's title/tags requests) gets eaten and returns empty content.
                # Treat the meta budget as a FLOOR: take the larger of client vs meta so
                # there is room for reasoning + the short answer. The model stops early
                # (finish=stop), so the generous ceiling costs nothing in practice.
                body["max_tokens"] = max(cur, cap) if isinstance(cur, int) else cap
            else:
                body["max_tokens"] = min(cur, cap) if isinstance(cur, int) else cap
        meta_think = meta_cfg.get("thinking", {}) or {}
        meta_effort = meta_think.get("effort")
        thinking_enabled = meta_think.get("enabled", False)

    if think_enabled is not None:
        thinking_enabled = think_enabled

    effort = think_effort
    budget_tokens = think_budget

    if pt_mode == "budget":
        if effort is None and meta_effort:
            effort = resolve_effort(card, meta_effort)
        if "reasoning_effort" in body:
            effort = resolve_effort(card, _raw_effort(body.get("reasoning_effort")))
        elif effort is not None:
            effort = resolve_effort(card, effort)
        body.pop("reasoning_effort", None)
        if budget_tokens is None and isinstance(body.get("thinking_token_budget"), int):
            budget_tokens = body["thinking_token_budget"]
        if not thinking_enabled and effort is None:
            effort = pt.get("disabled_effort", "none")
        body = apply_thinking(
            card, body, thinking_enabled, effort=effort, budget_tokens=budget_tokens,
        )
    else:
        # Reasoning models spend the token budget on (now-stripped) reasoning before the
        # final answer. If the caller gave a small budget, reasoning eats it and leaves an
        # empty reply. So for reasoning models, auto-skip thinking when the budget is too
        # small to fit reasoning + an answer -- unless the caller explicitly asked for an
        # effort/thinking level (then honor their choice). Default/large budgets reason
        # normally. This honors max_tokens exactly and never returns empties.
        if "reasoning_effort" in body:
            resolved = resolve_effort(card, _raw_effort(body.get("reasoning_effort")))
            if resolved is None:
                body.pop("reasoning_effort", None)
            else:
                body["reasoning_effort"] = resolved

        THINK_MIN_BUDGET = 4096
        explicit_think = ("reasoning_effort" in body or "chat_template_kwargs" in body
                or isinstance(body.get("thinking_token_budget"), int))
        if (thinking_enabled and not explicit_think
                and (card.get("behavior", {}) or {}).get("reasoning_model")):
            mt = body.get("max_tokens")
            if isinstance(mt, int) and mt < THINK_MIN_BUDGET:
                thinking_enabled = False

        body = apply_thinking(card, body, thinking_enabled)
        # Effort/toggle models have no native thinking budget. If the caller gave
        # one (thinking_token_budget), fake it by capping max_tokens so reasoning
        # can't exceed the requested budget (still leaves room for the answer).
        if pt_mode in ("effort", "toggle"):
            tb = body.get("thinking_token_budget")
            if isinstance(tb, int) and tb > 0:
                reserve = pt.get("answer_reserve", 512)
                floor = tb + reserve
                cap = (card.get("limits", {}) or {}).get("max_completion_tokens")
                mt = body.get("max_tokens")
                if not isinstance(mt, int) or mt > floor:
                    body["max_tokens"] = min(floor, cap) if isinstance(cap, int) and cap > 0 else floor
            # Consumed by the fake-budget cap above; don't forward to upstream (vLLM
            # would reject the unknown field on an effort/toggle model).
            body.pop("thinking_token_budget", None)

    # Hard cap to the card's max_completion_tokens.
    cap = (card.get("limits", {}) or {}).get("max_completion_tokens")
    if isinstance(cap, int) and cap > 0:
        mt = body.get("max_tokens")
        if not isinstance(mt, int) or mt > cap:
            body["max_tokens"] = cap

    # Rewrite the model name if the backend expects a different served name.
    if info.get("upstream_model_id"):
        body["model"] = info["upstream_model_id"]
    return body, thinking_enabled


# ── Endpoints ──────────────────────────────────────────────────────────────────
def _derive_input_format(card: dict) -> dict:
    """Best-effort input shape when the card doesn't declare one explicitly."""
    catalog = card.get("catalog", {}) or {}
    explicit = catalog.get("input_format")
    if explicit:
        return explicit
    mtype = card.get("type", "chat")
    if mtype in ("embedding", "embed"):
        return {"input": "str or [str]", "model": card["id"]}
    if mtype == "reranker":
        return {"model": card["id"], "query": "str", "documents": "[str]"}
    base: dict[str, Any] = {
        "messages": "[{role,content}]",
        "max_tokens": "int",
        "stream": "bool",
    }
    if (card.get("behavior", {}) or {}).get("supports_vision"):
        base["messages"] = (
            "[{role,content:[{type:text},{type:image_url,"
            "image_url:{url:'data:image/jpeg;base64,...'}}]}]"
        )
    return base


def _model_entry(card: dict, isvc_state: dict) -> dict:
    """Build the public catalog entry for a model entirely from its card +
    live ISVC state. Schema is a superset of the POC (232) /v1/models shape."""
    catalog = card.get("catalog", {}) or {}
    limits = card.get("limits", {}) or {}
    behavior = card.get("behavior", {}) or {}
    endpoints = card.get("endpoints", {}) or {}
    routing = card.get("routing", {}) or {}
    scaling = card.get("scaling", {}) or {}
    k8s_name = routing.get("k8s_name") or card["id"]
    st = isvc_state.get(k8s_name, {}) or {}
    res = st.get("resources", {}) or {}

    source = catalog.get("source", "")
    source_url = catalog.get("source_url") or (
        f"https://huggingface.co/{source}" if "/" in str(source) else ""
    )
    return {
        # ── 232-compatible fields ───────────────────────────────────────────
        "id": card["id"],
        "object": "model",
        "created": 1700000000,
        "owned_by": catalog.get("owned_by", "alliance-canada"),
        "type": card.get("type", "chat"),
        "context_window": limits.get("context_window", 0),
        "max_completion_tokens": limits.get("max_completion_tokens", 0),
        "description": catalog.get("description")
        or catalog.get("description_short", ""),
        "endpoint": endpoints.get("primary", ""),
        "input_format": _derive_input_format(card),
        "source": source,
        "source_url": source_url,
        "tags": catalog.get("tags", []),
        "parameters": catalog.get("parameters", ""),
        "gpu": bool(res.get("gpus")) if res else bool(catalog.get("gpu", True)),
        # ── card-driven extras (richer than 232) ────────────────────────────
        "ready": st.get("ready", False),
        "license": catalog.get("license", ""),
        "precision": catalog.get("precision", ""),
        "framework": catalog.get("framework", ""),
        "domain": catalog.get("domain", ""),
        "subdomain": catalog.get("subdomain", ""),
        # Embedding-specific catalog info (0/absent for generative models).
        "embedding_dimensions": catalog.get("embedding_dimensions", 0),
        "capabilities": {
            "vision": behavior.get("supports_vision", False),
            "video": behavior.get("supports_video", False),
            "tools": behavior.get("supports_tools", False),
            "reasoning": behavior.get("reasoning_model", False),
            "system_prompt": behavior.get("supports_system_prompt", True),
        },
        "scaling": {
            "scale_to_zero": scaling.get("scale_to_zero", False),
            "min_replicas": scaling.get("min_replicas"),
            "cold_start_estimate": scaling.get("cold_start_estimate", ""),
        },
        # allocated compute footprint (live from the ISVC predictor spec)
        "resources": res,
    }


@app.get("/v1/models")
async def list_models(request: Request):
    # ?all=true → every model (full catalogue); default → chat-UI-suitable only.
    show_all = request.query_params.get("all", "").lower() in ("1", "true", "yes")
    with _STATE_LOCK:
        cards = list(CARDS.values())
        isvc_state = dict(ISVC_STATE)
    data = [
        _model_entry(c, isvc_state)
        for c in cards
        if show_all or c.get("type", "chat") == "chat"
    ]
    data.sort(key=lambda x: x["id"])
    return {"object": "list", "data": data}


# ── "How to use it" web page at GET / ──────────────────────────────────────────
# Same gateway route is reached as `/` on the main host and `/serving/api/` on the
# backup host (Traefik strips /serving/api → /). The /v1 API paths are untouched.
_MAIN_HOST = "https://inference.vulcan.alliancecan.ca"
_BACKUP_HOST = "https://inference.kubeflow.vulcan.alliancecan.ca"


def _backup_path(path: str) -> str:
    """Map a gateway path to its form on the backup host.
    /v1/messages → /anthropic/v1/messages (stripPrefix /anthropic);
    every other /v1/* → /serving/api/v1/* (stripPrefix /serving/api)."""
    if path.startswith("/v1/messages"):
        return f"/anthropic{path}"
    return f"/serving/api{path}"


def _entry_paths(entry: dict) -> tuple[str, str]:
    path = entry.get("endpoint") or ""
    if not path.startswith("/"):
        path = "/v1/chat/completions"
    return f"{_MAIN_HOST}{path}", f"{_BACKUP_HOST}{_backup_path(path)}"


def _usage_snippet(entry: dict) -> str:
    """One short curl line for the model's primary endpoint, both hosts."""
    t = (entry.get("type") or "chat").lower()
    ep = entry.get("endpoint") or "/v1/chat/completions"
    mid = entry["id"]
    main, backup = _entry_paths(entry)
    if ep.startswith("/v1/audio/transcriptions"):
        body = f"-F model={mid} -F file=@audio.wav"
    elif ep.startswith("/v1/audio/speech"):
        body = f'-H "Content-Type: application/json" -d \'{{"model":"{mid}","input":"hello"}}\''
    elif ep.startswith("/v1/embeddings"):
        body = f'-H "Content-Type: application/json" -d \'{{"model":"{mid}","input":"text"}}\''
    elif ep.startswith("/v1/rerank"):
        body = f'-H "Content-Type: application/json" -d \'{{"model":"{mid}","query":"q","documents":["a","b"]}}\''
    else:
        body = (f'-H "Content-Type: application/json" '
                f'-d \'{{"model":"{mid}","messages":[{{"role":"user","content":"hi"}}]}}\'')
    return f"curl {main} {body}\n#  backup: curl {backup} {body}"


def _catalog_html() -> str:
    with _STATE_LOCK:
        cards = list(CARDS.values())
        isvc_state = dict(ISVC_STATE)
    entries = sorted((_model_entry(c, isvc_state) for c in cards), key=lambda x: x["id"])
    n_ready = sum(1 for e in entries if e.get("ready"))

    def esc(s):
        return html.escape(str(s) if s is not None else "")

    def badge(label, cls):
        return f'<span class="badge {cls}">{esc(label)}</span>'

    cards_html = []
    for e in entries:
        cap = e.get("capabilities", {}) or {}
        facts = []
        if e.get("context_window"):
            facts.append(("context", f'{e["context_window"]:,}'))
        if e.get("max_completion_tokens"):
            facts.append(("max out", f'{e["max_completion_tokens"]:,}'))
        for k, label in (("parameters", "params"), ("precision", "precision"),
                         ("framework", "framework"), ("license", "license"),
                         ("domain", "domain")):
            if e.get(k):
                facts.append((label, e[k]))
        facts_html = "".join(
            f"<div><span class='k'>{esc(k)}</span><span class='v'>{esc(v)}</span></div>"
            for k, v in facts)
        tags = " ".join(badge(t, "tag") for t in (e.get("tags") or [])[:4])
        caps = []
        if cap.get("vision"): caps.append("vision")
        if cap.get("tools"): caps.append("tools")
        if cap.get("reasoning"): caps.append("reasoning")
        caps_html = " ".join(badge(c, "cap") for c in caps)
        search = " ".join(str(x) for x in (
            e["id"], e.get("type"), e.get("description"), e.get("domain"),
            e.get("subdomain"), *(e.get("tags") or []))).lower()
        main, backup = _entry_paths(e)
        cards_html.append(f"""
        <article class="card" data-search="{esc(search)}">
          <header>
            <h3>{esc(e["id"])}</h3>
            <span class="dot {'ok' if e.get('ready') else 'cold'}" title="{'ready' if e.get('ready') else 'cold/not-ready'}"></span>
          </header>
          <div class="badges">{badge(e.get('type','chat'),'type')}{badge('gpu' if e.get('gpu') else 'cpu','gpu' if e.get('gpu') else 'cpu')}{caps_html}{tags}</div>
          <p class="desc">{esc((e.get('description') or '').split('. ')[0][:240])}</p>
          <div class="facts">{facts_html}</div>
          <div class="ep">
            <div><span class="k">endpoint</span>
              <a href="{esc(main)}">{esc(main)}</a></div>
            <div><span class="k">backup</span>
              <a href="{esc(backup)}">{esc(backup)}</a></div>
          </div>
          <details><summary>curl example</summary>
            <pre>{esc(_usage_snippet(e))}</pre>
          </details>
        </article>""")

    cheatsheet = f"""
    <pre># OpenAI chat (main | backup)
curl {_MAIN_HOST}/v1/chat/completions -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \\
  -d '{{"model":"command-r-7b","messages":[{{"role":"user","content":"hi"}}]}}'
curl {_BACKUP_HOST}/serving/api/v1/chat/completions ...   # same, valid-LE host

# Anthropic messages (main | backup)
curl {_MAIN_HOST}/v1/messages       -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \\
  -d '{{"model":"command-r-7b","max_tokens":20,"messages":[{{"role":"user","content":"hi"}}]}}'
curl {_BACKUP_HOST}/anthropic/v1/messages ...             # same, valid-LE host

# Speech-to-text (multipart) — streaming: add  -F stream=true
curl {_MAIN_HOST}/v1/audio/transcriptions -H "Authorization: Bearer $KEY" -F model=whisper-large-v3 -F file=@audio.wav
curl {_BACKUP_HOST}/serving/api/v1/audio/transcriptions ...

# Embeddings / rerank
curl {_MAIN_HOST}/v1/embeddings  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{{"model":"bge-m3","input":"text"}}'
curl {_MAIN_HOST}/v1/rerank      -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{{"model":"bge-reranker-v2-m3","query":"q","documents":["a","b"]}}'

# Machine-readable catalogue:  GET {_MAIN_HOST}/v1/models   (or {_BACKUP_HOST}/serving/api/v1/models)</pre>"""

    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aleph Inference Gateway</title>
<style>
 :root {{--bg:#0e1116;--card:#161b22;--ink:#c9d1d9;--mut:#8b949e;--acc:#58a6ff;--ok:#3fb950;--cold:#f85149;--bd:#30363d;}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}}
 a{{color:var(--acc);text-decoration:none}} a:hover{{text-decoration:underline}}
 header.top{{padding:28px 24px 8px;max-width:1180px;margin:0 auto}}
 header.top h1{{margin:0 0 4px;font-size:28px}} header.top p{{color:var(--mut);margin:0 0 12px}}
 .hosts{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}} .host{{background:var(--card);border:1px solid var(--bd);
 border-radius:8px;padding:8px 12px;font-size:13px}} .host b{{color:var(--mut);font-weight:500;display:block;font-size:11px;text-transform:uppercase}}
 .toolbar{{max-width:1180px;margin:14px auto 0;padding:0 24px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}}
 input.srch{{flex:1;min-width:220px;background:var(--card);border:1px solid var(--bd);color:var(--ink);
 border-radius:8px;padding:10px 12px;font-size:15px}} .count{{color:var(--mut);font-size:13px}}
 details.cheat{{max-width:1180px;margin:16px auto 0;padding:0 24px}}
 details.cheat summary{{cursor:pointer;color:var(--acc);font-size:14px}}
 pre{{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:12px;overflow:auto;
 font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#9ca7b3;white-space:pre-wrap;word-break:break-word}}
 grid{{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));
 max-width:1180px;margin:16px auto 40px;padding:0 24px}}
 .card{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px}}
 .card header{{display:flex;justify-content:space-between;align-items:center}}
 .card h3{{margin:0;font-size:16px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#fff;word-break:break-all}}
 .dot{{width:10px;height:10px;border-radius:50%;display:inline-block;flex:none}} .ok{{background:var(--ok)}} .cold{{background:var(--cold);opacity:.5}}
 .badges{{display:flex;gap:6px;flex-wrap:wrap}} .badge{{font-size:11px;padding:2px 7px;border-radius:10px;border:1px solid var(--bd);color:var(--mut)}}
 .badge.type{{color:#79c0ff;border-color:#1f6feb}} .badge.gpu{{color:var(--ok);border-color:#238636}} .badge.cpu{{color:var(--mut)}}
 .badge.cap{{color:#d2a8ff;border-color:#6e40c9}} .badge.tag{{color:var(--mut)}}
 .desc{{margin:0;color:var(--mut);font-size:13px}}
 .facts{{display:grid;grid-template-columns:repeat(2,1fr);gap:2px 12px;font-size:12px}}
 .facts div{{display:flex;justify-content:space-between;gap:6px}} .k{{color:var(--mut)}} .v{{color:var(--ink);text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
 .ep{{font-size:11px;display:flex;flex-direction:column;gap:2px}} .ep .k{{display:inline-block;width:52px}}
 .card details summary{{cursor:pointer;color:var(--acc);font-size:12px}} .card pre{{margin:6px 0 0;font-size:11px}}
 footer{{max-width:1180px;margin:0 auto 40px;padding:0 24px;color:var(--mut);font-size:12px}}
</style></head><body>
<header class="top">
 <h1>Aleph Inference Gateway</h1>
 <p>OpenAI- &amp; Anthropic-compatible inference on the Vulcan cluster. {len(entries)} models discovered ({n_ready} ready).
    Pick a host below (both serve every endpoint); the main host uses a self-signed cert, the backup a valid Let&rsquo;s Encrypt cert.</p>
 <div class="hosts">
   <div class="host"><b>main (self-signed)</b><a href="{_MAIN_HOST}/">{_MAIN_HOST}/</a></div>
   <div class="host"><b>backup (valid LE cert)</b><a href="{_BACKUP_HOST}/serving/api/">{_BACKUP_HOST}/serving/api/</a></div>
 </div>
</header>
<div class="toolbar">
 <input class="srch" id="q" placeholder="Search models by name, type, domain, tag…" autocomplete="off">
 <span class="count" id="cnt"></span>
</div>
<details class="cheat"><summary>How to use it — curl cheatsheet (both hosts)</summary>{cheatsheet}</details>
<grid id="grid">{''.join(cards_html)}</grid>
<footer>Machine-readable: <a href="/v1/models">/v1/models</a> · health: <a href="/healthz">/healthz</a> ·
 metrics: <a href="/metrics">/metrics</a>. Public traffic is authenticated by a Tyk API key (<code>Authorization: Bearer $KEY</code>).</footer>
<script>
 const cards=[...document.querySelectorAll('.card')];
 const cnt=document.getElementById('cnt');
 function upd(){{const q=document.getElementById('q').value.toLowerCase().trim();let n=0;
  cards.forEach(c=>{{const m=!q||c.dataset.search.includes(q);c.style.display=m?'':'none';n+=m;}});
  cnt.textContent=n+' / '+cards.length+' models';}}
 document.getElementById('q').addEventListener('input',upd);upd();
</script>
</body></html>"""


@app.get("/", include_in_schema=False)
async def catalog_page():
    return HTMLResponse(_catalog_html())


def _strips_thinking(info: dict) -> bool:
    """Card opt-in: remove reasoning/thinking from responses (only the answer ships)."""
    return bool(((info.get("card", {}) or {}).get("behavior", {}) or {}).get("strips_thinking"))


def _manages_thinking(info: dict) -> bool:
    """A model whose reasoning the gateway exposes/strips per-request
    (param_translation.thinking.mode in budget/effort/toggle/always_on). For these we
    expose reasoning when thinking is ON and strip+cap when OFF. always_on models
    (qwq, r1-distill) can't stop reasoning, so OFF = strip the reasoning + cap max_tokens
    (reduce what fits). none / non-reasoning models are not managed."""
    mode = (((info.get("card", {}) or {}).get("param_translation", {}) or {})
            .get("thinking", {}) or {}).get("mode", "none")
    return mode in ("budget", "effort", "toggle", "always_on")


def _expose_reasoning(info: dict, thinking_on: bool) -> bool:
    """Should reasoning ship to the client for this request?
    Managed-thinking models: expose when on, hide when off.
    Others: legacy behavior (hide iff the card sets strips_thinking)."""
    if _manages_thinking(info):
        return thinking_on
    return not _strips_thinking(info)


def _off_token_cap(info: dict, body: dict) -> dict:
    """When thinking is OFF for a managed model, restrict the token budget so the
    model can't burn tokens on (about-to-be-stripped) reasoning. Effort models
    have no native thinking budget, so we fake one with a max_tokens cap
    (card's param_translation.thinking.off_max_tokens, default 2048)."""
    pt = (((info.get("card", {}) or {}).get("param_translation", {}) or {})
          .get("thinking", {}) or {})
    cap = pt.get("off_max_tokens", 2048)
    mt = body.get("max_tokens")
    body["max_tokens"] = min(mt, cap) if isinstance(mt, int) else cap
    return body


def _supports_tools(info: dict) -> bool:
    return bool(((info.get("card", {}) or {}).get("behavior", {}) or {}).get("supports_tools"))


def _supports_vision(info: dict) -> bool:
    return bool(((info.get("card", {}) or {}).get("behavior", {}) or {}).get("supports_vision"))


def _has_vision_content_openai(messages: list) -> bool:
    """Check if OpenAI-format messages contain image_url blocks."""
    for msg in (messages or []):
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "image_url":
                    return True
    return False


def _has_vision_content_anthropic(messages: list) -> bool:
    """Check if Anthropic-format messages contain image blocks."""
    for msg in (messages or []):
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "image":
                    return True
    return False


def _tools_unsupported_error(model_id: str):
    """Clean 400 when a client sends tools to a model whose card has no tool support,
    instead of leaking the upstream engine's raw 'enable-auto-tool-choice' 400."""
    return JSONResponse(
        {"error": {
            "message": (f"model '{model_id}' does not support tool calling. "
                        "Retry without the 'tools' parameter."),
            "type": "invalid_request_error",
            "code": "tools_unsupported",
        }}, 400)


def _vision_unsupported_error(model_id: str):
    """Clean 400 when a client sends image content to a model whose card has no vision support."""
    return JSONResponse(
        {"error": {
            "message": (f"model '{model_id}' does not support vision/image input. "
                        "Retry with text-only messages."),
            "type": "invalid_request_error",
            "code": "vision_unsupported",
        }}, 400)


def strip_reasoning_obj(data: dict) -> dict:
    """Drop reasoning fields from a non-streaming OpenAI chat response (in place)."""
    for ch in data.get("choices", []) or []:
        msg = ch.get("message")
        if isinstance(msg, dict):
            msg.pop("reasoning", None)
            msg.pop("reasoning_content", None)
    return data


async def _forward(info: dict, path: str, body: bytes, stream: bool, *,
                   strip_reasoning: bool | None = None,
                   log_ctx: dict | None = None):
    url = upstream_url(path)
    headers = upstream_headers(info)
    strip = _strips_thinking(info) if strip_reasoning is None else strip_reasoning
    if stream and not info.get("no_stream"):
        async def gen():
            t0 = time.monotonic()
            status_code = 200
            captured_usage = None
            async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
                async with c.stream("POST", url, content=body, headers=headers) as r:
                    status_code = r.status_code
                    # Fast raw passthrough only when we neither strip nor account.
                    if not strip and not log_ctx:
                        async for chunk in r.aiter_raw():
                            yield chunk
                        return
                    # Parse SSE lines: optionally drop reasoning deltas (strip) and
                    # capture the final usage object (log_ctx, needs include_usage).
                    buf = ""
                    async for piece in r.aiter_text():
                        buf += piece
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            s = line.strip()
                            if not s.startswith("data:") or s[5:].strip() == "[DONE]":
                                yield (line + "\n").encode()
                                continue
                            try:
                                obj = json.loads(s[5:].strip())
                            except Exception:
                                yield (line + "\n").encode()
                                continue
                            if log_ctx and obj.get("usage"):
                                captured_usage = obj["usage"]
                            if not strip:
                                yield (line + "\n").encode()
                                continue
                            for ch in obj.get("choices", []) or []:
                                d = ch.get("delta")
                                if isinstance(d, dict):
                                    d.pop("reasoning", None)
                                    d.pop("reasoning_content", None)
                            yield ("data: " + json.dumps(obj) + "\n").encode()
                    if buf:
                        yield buf.encode()
            if log_ctx:
                latency_ms = int((time.monotonic() - t0) * 1000)
                _log_usage(log_ctx["request"], info, endpoint=log_ctx["endpoint"],
                           api=log_ctx["api"], status=status_code,
                           latency_ms=latency_ms, usage_obj=captured_usage,
                           stream=True)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        # Ensure no_stream models never get stream=true upstream
        if info.get("no_stream"):
            try:
                b = json.loads(body)
                b["stream"] = False
                body = json.dumps(b).encode()
            except Exception:
                pass
        r = await c.post(url, content=body, headers=headers)
    if log_ctx:
        latency_ms = int((time.monotonic() - t0) * 1000)
        u = None
        try:
            u = r.json().get("usage")
        except Exception:
            u = None
        _log_usage(log_ctx["request"], info, endpoint=log_ctx["endpoint"],
                   api=log_ctx["api"], status=r.status_code, latency_ms=latency_ms,
                   usage_obj=u, stream=False)
    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "application/json"),
    )


@app.post("/v1/embeddings")
async def embeddings(request: Request):
    _METRICS["requests_total"] += 1
    body = await request.body()
    try:
        parsed = json.loads(body)
    except Exception:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": "invalid JSON body"}, 400)
    model_id = parsed.get("model")
    info = resolve(model_id) if model_id else None
    if not info:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": f"model '{model_id}' not found"}, 404)
    cold = await _guard_cold(request, info, "/v1/embeddings", "openai")
    if cold is not None:
        return cold
    if info.get("upstream_model_id"):
        parsed["model"] = info["upstream_model_id"]
        body = json.dumps(parsed).encode()
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        r = await c.post(upstream_url("/v1/embeddings"), content=body,
                         headers=upstream_headers(info))
    latency_ms = int((time.monotonic() - t0) * 1000)
    if r.status_code != 200:
        _METRICS["requests_error"] += 1
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))
    try:
        data = r.json()
        data["resources"] = resource_block(info, latency_ms)
        _log_usage(request, info, endpoint="/v1/embeddings", api="openai",
                   status=200, latency_ms=latency_ms, usage_obj=data.get("usage"))
        return JSONResponse(data)
    except Exception:
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))


@app.post("/v1/rerank")
async def rerank(request: Request):
    """Cohere/Jina-style rerank -> TEI's native /rerank ({query, texts}) and back.
    TEI only exposes /rerank with `texts`; we accept `documents` (str or {text})
    and return Cohere-shaped {results:[{index, relevance_score, document?}]}."""
    _METRICS["requests_total"] += 1
    body = await request.body()
    try:
        parsed = json.loads(body)
    except Exception:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": "invalid JSON body"}, 400)
    model_id = parsed.get("model")
    info = resolve(model_id) if model_id else None
    if not info:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": f"model '{model_id}' not found"}, 404)
    cold = await _guard_cold(request, info, "/v1/rerank", "cohere")
    if cold is not None:
        return cold
    query = parsed.get("query")
    docs = parsed.get("documents")
    if docs is None:
        docs = parsed.get("texts") or []
    texts = [d if isinstance(d, str) else (d.get("text", "") if isinstance(d, dict) else str(d))
             for d in docs]
    top_n = parsed.get("top_n")
    return_documents = bool(parsed.get("return_documents"))
    tei_payload = {"query": query or "", "texts": texts}
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        r = await c.post(upstream_url("/rerank"), content=json.dumps(tei_payload).encode(),
                         headers=upstream_headers(info))
    latency_ms = int((time.monotonic() - t0) * 1000)
    if r.status_code != 200:
        _METRICS["requests_error"] += 1
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))
    try:
        ranked = r.json()  # TEI: [{"index": int, "score": float}, ...] sorted desc
        results = []
        for item in ranked:
            idx = item.get("index")
            entry = {"index": idx, "relevance_score": item.get("score")}
            if return_documents and isinstance(idx, int) and 0 <= idx < len(texts):
                entry["document"] = {"text": texts[idx]}
            results.append(entry)
        if isinstance(top_n, int) and top_n >= 0:
            results = results[:top_n]
        _log_usage(request, info, endpoint="/v1/rerank", api="cohere",
                   status=200, latency_ms=latency_ms)
        return JSONResponse({"model": model_id, "results": results,
                             "resources": resource_block(info, latency_ms)})
    except Exception:
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))


@app.post("/v1/chat/completions")
async def chat(request: Request):
    _METRICS["requests_total"] += 1
    raw = await request.body()
    try:
        parsed = json.loads(raw)
    except Exception:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": "invalid JSON body"}, 400)
    model_id = parsed.get("model")
    info = resolve(model_id) if model_id else None
    if not info:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": f"model '{model_id}' not found"}, 404)
    if not info["ready"]:
        return JSONResponse(
            {
                "error": {
                    "message": f"model '{model_id}' not ready",
                    "code": "model_not_ready",
                }
            },
            503,
        )
    if parsed.get("tools") and not _supports_tools(info):
        _METRICS["requests_error"] += 1
        return _tools_unsupported_error(model_id)
    if _has_vision_content_openai(parsed.get("messages")) and not _supports_vision(info):
        _METRICS["requests_error"] += 1
        return _vision_unsupported_error(model_id)
    cold = await _guard_cold(request, info, "/v1/chat/completions", "openai")
    if cold is not None:
        return cold
    parsed, thinking_on = prepare_chat(info, parsed)
    if _manages_thinking(info) and not thinking_on:
        parsed = _off_token_cap(info, parsed)
    stream = bool(parsed.get("stream"))
    if stream and not info.get("no_stream"):
        # Ask the engine to emit a final usage chunk so we can account streamed calls.
        so = parsed.get("stream_options")
        if isinstance(so, dict):
            so.setdefault("include_usage", True)
        else:
            parsed["stream_options"] = {"include_usage": True}
        return await _forward(info, "/v1/chat/completions", json.dumps(parsed).encode(), True,
                              strip_reasoning=not _expose_reasoning(info, thinking_on),
                              log_ctx={"request": request,
                                       "endpoint": "/v1/chat/completions",
                                       "api": "openai"})

    # no_stream card or non-streaming request: force stream=false upstream
    parsed["stream"] = False
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        r = await c.post(upstream_url("/v1/chat/completions"),
                         content=json.dumps(parsed).encode(),
                         headers=upstream_headers(info))
    latency_ms = int((time.monotonic() - t0) * 1000)
    if r.status_code != 200:
        _METRICS["requests_error"] += 1
        _log_usage(request, info, endpoint="/v1/chat/completions", api="openai",
                   status=r.status_code, latency_ms=latency_ms)
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))
    try:
        data = r.json()
        if not _expose_reasoning(info, thinking_on):
            strip_reasoning_obj(data)
        data["resources"] = resource_block(info, latency_ms)
        _log_usage(request, info, endpoint="/v1/chat/completions", api="openai",
                   status=200, latency_ms=latency_ms, usage_obj=data.get("usage"))
        return JSONResponse(data)
    except Exception:
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))


@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    """Native Anthropic Messages endpoint: translate to OpenAI, run the chat
    pipeline, translate the response (and SSE stream) back to Anthropic shape."""
    _METRICS["requests_total"] += 1
    raw = await request.body()
    try:
        a_body = json.loads(raw)
    except Exception:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": "invalid JSON body"}, 400)

    model_id = a_body.get("model")
    info = resolve(model_id) if model_id else None
    if not info:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": f"model '{model_id}' not found"}, 404)
    if info["type"] not in ("chat",):
        _METRICS["requests_error"] += 1
        return JSONResponse(
            {"error": {
                "message": (f"model '{model_id}' does not support the Anthropic Messages API "
                            f"(type={info['type']}). Use /v1/chat/completions or a model-specific "
                            f"endpoint instead."),
                "type": "invalid_request_error",
                "code": "anthropic_unsupported",
            }}, 400)
    if not info["ready"]:
        return JSONResponse(
            {"error": {"message": f"model '{model_id}' not ready",
                       "code": "model_not_ready"}}, 503)
    if a_body.get("tools") and not _supports_tools(info):
        _METRICS["requests_error"] += 1
        return _tools_unsupported_error(model_id)
    if _has_vision_content_anthropic(
        [m for m in (a_body.get("messages") or []) if isinstance(m, dict)]
    ) and not _supports_vision(info):
        _METRICS["requests_error"] += 1
        return _vision_unsupported_error(model_id)
    cold = await _guard_cold(request, info, "/v1/messages", "anthropic")
    if cold is not None:
        return cold

    enabled, effort, budget = anth_desired_thinking(a_body)
    pt_mode = ((info["card"].get("param_translation", {}) or {})
               .get("thinking", {}) or {}).get("mode", "none")
    oai = anth_to_openai(a_body)
    if pt_mode == "budget":
        oai, thinking_on = prepare_chat(
            info, oai, think_enabled=enabled, think_effort=effort, think_budget=budget,
        )
    else:
        oai, _ = prepare_chat(info, oai)
        # Honor the client's requested thinking level. Anthropic budget_tokens / effort
        # map to the model's native effort (gpt-oss: low/medium/high); inject it before
        # apply_thinking so the caller's level wins over the card default.
        if enabled and effort and pt_mode == "effort":
            resolved = resolve_effort(info["card"], effort)
            if resolved:
                oai["reasoning_effort"] = resolved
        oai = apply_thinking(info["card"], oai, enabled)
        thinking_on = enabled
    if _manages_thinking(info) and not thinking_on:
        oai = _off_token_cap(info, oai)
    expose = _expose_reasoning(info, thinking_on)
    stream = bool(a_body.get("stream"))
    url = upstream_url("/v1/chat/completions")
    headers = upstream_headers(info)

    if stream and not info.get("no_stream"):
        oai["stream"] = True
        oai.setdefault("stream_options", {"include_usage": True})

        async def gen():
            yield b"".join(anth_stream_start_events(model_id))
            finish = None
            out_tokens = 0
            captured_usage = None
            buf = ""
            # Content blocks are opened lazily: index/track the currently-open
            # block so a tool-call response becomes a tool_use block instead of
            # the function name leaking through as text.
            cur_idx = -1            # index of the open content block (-1 = none)
            cur_kind = None         # "text" | "tool_use"
            tool_state: dict[int, dict] = {}   # per tool-call index -> {id,name,args_sent}
            t0 = time.monotonic()

            def _open_block(kind: str, **block_fields) -> bytes:
                nonlocal cur_idx, cur_kind
                if cur_idx >= 0:
                    out = _anth_sse("content_block_stop",
                                    {"type": "content_block_stop", "index": cur_idx})
                else:
                    out = b""
                cur_idx += 1
                cur_kind = kind
                return out + _anth_sse("content_block_start", {
                    "type": "content_block_start", "index": cur_idx,
                    "content_block": {"type": kind, **block_fields},
                })

            async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
                async with c.stream("POST", url, content=json.dumps(oai).encode(),
                                    headers=headers) as r:
                    async for chunk in r.aiter_text():
                        buf += chunk
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            obj = anth_parse_openai_sse_line(line)
                            if not obj:
                                continue
                            for ch in obj.get("choices", []) or []:
                                delta = ch.get("delta") or {}
                                # ---- reasoning -> thinking block (only when exposing) ----
                                reasoning = delta.get("reasoning") or delta.get("reasoning_content")
                                if reasoning and expose:
                                    if cur_kind != "thinking":
                                        yield _open_block("thinking", thinking="", signature="")
                                    yield _anth_sse("content_block_delta", {
                                        "type": "content_block_delta", "index": cur_idx,
                                        "delta": {"type": "thinking_delta", "thinking": reasoning},
                                    })
                                # ---- text content ----
                                text = delta.get("content")
                                if text:
                                    if cur_kind != "text":
                                        yield _open_block("text", text="")
                                    yield _anth_sse("content_block_delta", {
                                        "type": "content_block_delta", "index": cur_idx,
                                        "delta": {"type": "text_delta", "text": text},
                                    })
                                # ---- tool calls ----
                                for tc in delta.get("tool_calls") or []:
                                    tidx = tc.get("index", 0)
                                    fn = tc.get("function") or {}
                                    st = tool_state.get(tidx)
                                    if st is None:
                                        tc_id = tc.get("id") or ("toolu_" + uuid.uuid4().hex[:24])
                                        st = {"id": tc_id, "name": fn.get("name", ""),
                                              "args_sent": ""}
                                        tool_state[tidx] = st
                                        yield _open_block("tool_use", id=tc_id,
                                                          name=st["name"], input={})
                                    args = fn.get("arguments") or ""
                                    if args and args != st["args_sent"]:
                                        new = (args[len(st["args_sent"]):]
                                               if args.startswith(st["args_sent"]) else args)
                                        st["args_sent"] = args
                                        yield _anth_sse("content_block_delta", {
                                            "type": "content_block_delta", "index": cur_idx,
                                            "delta": {"type": "input_json_delta",
                                                      "partial_json": new},
                                        })
                                if ch.get("finish_reason"):
                                    finish = ch["finish_reason"]
                            u = obj.get("usage")
                            if u:
                                out_tokens = u.get("completion_tokens", out_tokens)
                                captured_usage = u
            if cur_idx >= 0:
                yield _anth_sse("content_block_stop",
                                {"type": "content_block_stop", "index": cur_idx})
            else:
                # Empty turn (no text, no tool calls — e.g. immediate stop or a
                # fully stripped thinking response): emit a placeholder text
                # block so the message always carries at least one content block.
                yield _anth_sse("content_block_start", {
                    "type": "content_block_start", "index": 0,
                    "content_block": {"type": "text", "text": ""},
                })
                yield _anth_sse("content_block_stop",
                                {"type": "content_block_stop", "index": 0})
            latency_ms = int((time.monotonic() - t0) * 1000)
            for ev in anth_stream_stop_events(
                finish, out_tokens, resource_block(info, latency_ms)
            ):
                yield ev
            _log_usage(request, info, endpoint="/v1/messages", api="anthropic",
                       status=200, latency_ms=latency_ms, usage_obj=captured_usage,
                       stream=True)

        return StreamingResponse(
            gen(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    oai["stream"] = False
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        r = await c.post(url, content=json.dumps(oai).encode(), headers=headers)
    latency_ms = int((time.monotonic() - t0) * 1000)
    if r.status_code != 200:
        _METRICS["requests_error"] += 1
        _log_usage(request, info, endpoint="/v1/messages", api="anthropic",
                   status=r.status_code, latency_ms=latency_ms)
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))
    raw_oai = r.json()
    out = anth_from_openai(raw_oai, model_id, include_thinking=expose)
    out["resources"] = resource_block(info, latency_ms)
    _log_usage(request, info, endpoint="/v1/messages", api="anthropic",
               status=200, latency_ms=latency_ms, usage_obj=raw_oai.get("usage"))
    return JSONResponse(out)


@app.post("/v1/audio/transcriptions")
async def audio_transcriptions(request: Request):
    """OpenAI-compatible STT (multipart). Resolve the model from the form, then
    forward the RAW body unchanged so the multipart boundary survives, with raw
    streaming passthrough when stream=true. Registered before the catch-all so
    multipart uploads don't hit forward_custom's JSON-only model parser.

    Backend e.g. speaches (faster-whisper), reached via the card's k8s_name like
    any other model. Non-multipart (JSON) requests are also accepted.
    """
    _METRICS["requests_total"] += 1
    ctype = request.headers.get("content-type", "")
    model_id = None
    stream = False
    if ctype.lower().startswith("multipart/"):
        # form() populates+ caches the body; raw bytes come back identically below.
        try:
            form = await request.form()
        except Exception:
            form = None
        if form is not None:
            m = form.get("model")
            model_id = m if isinstance(m, str) else None
            s = form.get("stream")
            stream = (s if isinstance(s, str) else "").lower() in ("1", "true", "yes")
    body = await request.body()
    if model_id is None:
        # JSON fallback: {model, stream, ...}
        try:
            parsed = json.loads(body)
            model_id = parsed.get("model")
            stream = bool(parsed.get("stream"))
        except Exception:
            model_id = None
    if not model_id:
        _METRICS["requests_error"] += 1
        return JSONResponse(
            {"error": "model field required (multipart 'model' or JSON 'model')"}, 400)
    info = resolve(model_id)
    if not info:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": f"model '{model_id}' not found"}, 404)
    cold = await _guard_cold(request, info, "/v1/audio/transcriptions", "openai")
    if cold is not None:
        return cold
    # Forward the original multipart bytes with the original Content-Type so the
    # boundary is preserved. Host header still routes to the predictor.
    headers = upstream_headers(info, content_type=ctype or "application/json")
    url = upstream_url("/v1/audio/transcriptions")
    log_kwargs = {"endpoint": "/v1/audio/transcriptions", "api": "openai"}

    if stream and not info.get("no_stream"):
        # Raw byte passthrough — STT streams text/SSE chunks we must not rewrite
        # (NOT the chat-aware _forward stream branch that parses OpenAI choices).
        async def gen():
            t0 = time.monotonic()
            status_code = 200
            async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
                async with c.stream("POST", url, content=body, headers=headers) as r:
                    status_code = r.status_code
                    async for chunk in r.aiter_raw():
                        yield chunk
            latency_ms = int((time.monotonic() - t0) * 1000)
            _log_usage(request, info, status=status_code, latency_ms=latency_ms,
                       stream=True, **log_kwargs)
        return StreamingResponse(
            gen(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        r = await c.post(url, content=body, headers=headers)
    latency_ms = int((time.monotonic() - t0) * 1000)
    _log_usage(request, info, status=r.status_code, latency_ms=latency_ms, **log_kwargs)
    if r.status_code >= 400:
        _METRICS["requests_error"] += 1
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type", "application/json"))


@app.api_route("/v1/{path:path}", methods=["POST", "GET"])
async def forward_custom(path: str, request: Request):
    """Catch-all forward for science / custom server.py models. Registered last."""
    _METRICS["requests_total"] += 1
    body = await request.body()
    model_id = None
    if body:
        try:
            model_id = json.loads(body).get("model")
        except Exception:
            model_id = None
    if not model_id:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": "model field required in request body"}, 400)
    info = resolve(model_id)
    if not info:
        _METRICS["requests_error"] += 1
        return JSONResponse({"error": f"model '{model_id}' not found"}, 404)
    cold = await _guard_cold(request, info, f"/v1/{path}", "custom")
    if cold is not None:
        return cold
    return await _forward(info, f"/v1/{path}", body, stream=False,
                          log_ctx={"request": request, "endpoint": f"/v1/{path}",
                                   "api": "custom"})


@app.get("/healthz")
async def healthz():
    # Alive if the discovery seed completed at least once.
    ok = _DISCOVERY["cards_seeded"] and _DISCOVERY["isvc_seeded"]
    return JSONResponse({"status": "ok" if ok else "starting"}, 200 if ok else 503)


@app.get("/readyz")
async def readyz():
    with _STATE_LOCK:
        n = len(CARDS)
    if n >= 1:
        return JSONResponse({"status": "ready", "cards": n}, 200)
    return JSONResponse({"status": "no cards", "cards": 0}, 503)


@app.get("/metrics")
async def metrics():
    with _STATE_LOCK:
        cards_total = len(CARDS)
        ready = sum(1 for c in CARDS.values()
                    if ISVC_STATE.get((c.get("routing", {}) or {}).get("k8s_name") or c["id"], {}).get("ready"))
    lines = [
        "# HELP gateway_requests_total Total requests handled.",
        "# TYPE gateway_requests_total counter",
        f"gateway_requests_total {_METRICS['requests_total']}",
        "# HELP gateway_requests_error_total Total errored requests.",
        "# TYPE gateway_requests_error_total counter",
        f"gateway_requests_error_total {_METRICS['requests_error']}",
        "# HELP gateway_models_total Discovered model cards.",
        "# TYPE gateway_models_total gauge",
        f"gateway_models_total {cards_total}",
        "# HELP gateway_models_ready Models with a ready ISVC.",
        "# TYPE gateway_models_ready gauge",
        f"gateway_models_ready {ready}",
    ]
    counters = usage.snapshot()
    if counters:
        lines += [
            "# HELP gateway_model_requests_total Served requests per model.",
            "# TYPE gateway_model_requests_total counter",
        ]
        lines += [f'gateway_model_requests_total{{model="{m}"}} {c["requests"]}'
                  for m, c in counters.items()]
        lines += [
            "# HELP gateway_model_prompt_tokens_total Prompt tokens per model.",
            "# TYPE gateway_model_prompt_tokens_total counter",
        ]
        lines += [f'gateway_model_prompt_tokens_total{{model="{m}"}} {c["prompt_tokens"]}'
                  for m, c in counters.items()]
        lines += [
            "# HELP gateway_model_completion_tokens_total Completion tokens per model.",
            "# TYPE gateway_model_completion_tokens_total counter",
        ]
        lines += [f'gateway_model_completion_tokens_total{{model="{m}"}} {c["completion_tokens"]}'
                  for m, c in counters.items()]
        lines += [
            "# HELP gateway_model_cold_starts_total Cold-start (scale-from-zero) events per model.",
            "# TYPE gateway_model_cold_starts_total counter",
        ]
        lines += [f'gateway_model_cold_starts_total{{model="{m}"}} {c["cold_starts"]}'
                  for m, c in counters.items()]
        lines += [
            "# HELP gateway_model_gpu_seconds_total Approx GPU-seconds (gpus*latency) per model.",
            "# TYPE gateway_model_gpu_seconds_total counter",
        ]
        lines += [f'gateway_model_gpu_seconds_total{{model="{m}"}} {round(c["gpu_seconds"], 3)}'
                  for m, c in counters.items()]
    return Response("\n".join(lines) + "\n", media_type="text/plain")
