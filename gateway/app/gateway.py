"""
Card-driven model inference gateway for cluster 230 (HAMi / KServe / Knative).

Design: GATEWAY-ARCHITECTURE.md. Models declare themselves via `details.yaml`
ConfigMaps (label `model-details=true`). The gateway reads these cards, merges
live state from InferenceServices, and routes requests to model pods through the
knative-local-gateway. No model names are hardcoded.

Phase 1 scope: discovery (cards + ISVC watch), /v1/models, embeddings + chat
handlers, /v1/{custom} forward catch-all, /healthz /readyz /metrics.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from kubernetes import client, config, watch

import anthropic_xlate as anth

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


@app.on_event("startup")
async def _startup() -> None:
    _load_kube()
    seed_cards()
    seed_isvcs()
    threading.Thread(target=watch_cards, daemon=True).start()
    threading.Thread(target=watch_isvcs, daemon=True).start()
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
    (DCGM / HAMi exporter) and is not wired yet — see GATEWAY-ARCHITECTURE.md.
    """
    block = {"model": info["id"]}
    block.update(info.get("resources", {}) or {})
    block["latency_ms"] = latency_ms
    return block


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


def detect_meta_task(body: dict) -> str | None:
    msgs = body.get("messages") or []
    if len(msgs) == 1 and msgs[0].get("role") == "user":
        prompt = msgs[0].get("content") or ""
        if isinstance(prompt, str):
            for task, signal in _OWUI_SIGNALS.items():
                if signal in prompt:
                    return task
    return None


# OpenAI's reasoning_effort value set (none/minimal/low/medium/high/xhigh) and
# Anthropic's adaptive effort (low/medium/high/xhigh/max) both get folded onto the
# 3 levels our backends actually support (gpt-oss: low/medium/high). We never error
# on an unknown level; reasoning is stripped from the response either way.
_EFFORT_ALIASES = {
    "none": "low", "minimal": "low", "low": "low",
    "medium": "medium", "med": "medium",
    "high": "high", "xhigh": "high", "max": "high",
}


def normalize_effort(v) -> str | None:
    """Map any OpenAI/Anthropic effort token to low|medium|high (None if unrecognized)."""
    if v is None:
        return None
    if isinstance(v, dict):            # OpenAI object form: {"effort": "...", "summary": "..."}
        v = v.get("effort")
    return _EFFORT_ALIASES.get(str(v).lower()) if v is not None else None


def apply_thinking(card: dict, body: dict, enabled: bool) -> dict:
    """Translate a desired thinking on/off into the model's dialect via the card."""
    pt = (card.get("param_translation", {}) or {}).get("thinking", {}) or {}
    mode = pt.get("mode", "none")
    if mode in ("none", "always_on"):
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


def prepare_chat(info: dict, body: dict) -> dict:
    card = info["card"]
    body = apply_defaults(card, body)

    meta = detect_meta_task(body)
    thinking_enabled = True
    chat_defaults = (card.get("defaults", {}) or {}).get("chat", {}) or {}
    thinking_enabled = (chat_defaults.get("thinking", {}) or {}).get("enabled", True)

    if meta:
        meta_cfg = ((card.get("defaults", {}) or {}).get("meta_tasks", {}) or {}).get(meta, {})
        if "max_tokens" in meta_cfg:
            cur = body.get("max_tokens")
            cap = meta_cfg["max_tokens"]
            body["max_tokens"] = min(cur, cap) if isinstance(cur, int) else cap
        thinking_enabled = (meta_cfg.get("thinking", {}) or {}).get("enabled", False)

    # Reasoning models spend the token budget on (now-stripped) reasoning before the
    # final answer. If the caller gave a small budget, reasoning eats it and leaves an
    # empty reply. So for reasoning models, auto-skip thinking when the budget is too
    # small to fit reasoning + an answer -- unless the caller explicitly asked for an
    # effort/thinking level (then honor their choice). Default/large budgets reason
    # normally. This honors max_tokens exactly and never returns empties.
    # Normalize OpenAI reasoning_effort (none/minimal/low/medium/high/xhigh, or the
    # {"effort":..} object form) onto the backend's low/medium/high. Unknown values
    # are dropped so we fall back to the card default instead of erroring upstream.
    if "reasoning_effort" in body:
        norm = normalize_effort(body.get("reasoning_effort"))
        if norm is None:
            body.pop("reasoning_effort", None)
        else:
            body["reasoning_effort"] = norm

    THINK_MIN_BUDGET = 4096
    explicit_think = "reasoning_effort" in body or "chat_template_kwargs" in body
    if (thinking_enabled and not explicit_think
            and (card.get("behavior", {}) or {}).get("reasoning_model")):
        mt = body.get("max_tokens")
        if isinstance(mt, int) and mt < THINK_MIN_BUDGET:
            thinking_enabled = False

    body = apply_thinking(card, body, thinking_enabled)

    # Hard cap to the card's max_completion_tokens.
    cap = (card.get("limits", {}) or {}).get("max_completion_tokens")
    if isinstance(cap, int) and cap > 0:
        mt = body.get("max_tokens")
        if not isinstance(mt, int) or mt > cap:
            body["max_tokens"] = cap

    # Rewrite the model name if the backend expects a different served name.
    if info.get("upstream_model_id"):
        body["model"] = info["upstream_model_id"]
    return body


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


def _strips_thinking(info: dict) -> bool:
    """Card opt-in: remove reasoning/thinking from responses (only the answer ships)."""
    return bool(((info.get("card", {}) or {}).get("behavior", {}) or {}).get("strips_thinking"))


def _supports_tools(info: dict) -> bool:
    return bool(((info.get("card", {}) or {}).get("behavior", {}) or {}).get("supports_tools"))


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


def strip_reasoning_obj(data: dict) -> dict:
    """Drop reasoning fields from a non-streaming OpenAI chat response (in place)."""
    for ch in data.get("choices", []) or []:
        msg = ch.get("message")
        if isinstance(msg, dict):
            msg.pop("reasoning", None)
            msg.pop("reasoning_content", None)
    return data


async def _forward(info: dict, path: str, body: bytes, stream: bool):
    url = upstream_url(path)
    headers = upstream_headers(info)
    strip = _strips_thinking(info)
    if stream and not info.get("no_stream"):
        async def gen():
            async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
                async with c.stream("POST", url, content=body, headers=headers) as r:
                    if not strip:
                        async for chunk in r.aiter_raw():
                            yield chunk
                        return
                    # Reasoning-stripping pass: parse SSE lines, drop reasoning deltas.
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
                            for ch in obj.get("choices", []) or []:
                                d = ch.get("delta")
                                if isinstance(d, dict):
                                    d.pop("reasoning", None)
                                    d.pop("reasoning_content", None)
                            yield ("data: " + json.dumps(obj) + "\n").encode()
                    if buf:
                        yield buf.encode()

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        r = await c.post(url, content=body, headers=headers)
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
    cold = await cold_start_guard(info)
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
    cold = await cold_start_guard(info)
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
    cold = await cold_start_guard(info)
    if cold is not None:
        return cold
    parsed = prepare_chat(info, parsed)
    stream = bool(parsed.get("stream"))
    if stream and not info.get("no_stream"):
        return await _forward(info, "/v1/chat/completions", json.dumps(parsed).encode(), True)

    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        r = await c.post(upstream_url("/v1/chat/completions"),
                         content=json.dumps(parsed).encode(),
                         headers=upstream_headers(info))
    latency_ms = int((time.monotonic() - t0) * 1000)
    if r.status_code != 200:
        _METRICS["requests_error"] += 1
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))
    try:
        data = r.json()
        if _strips_thinking(info):
            strip_reasoning_obj(data)
        data["resources"] = resource_block(info, latency_ms)
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
    if not info["ready"]:
        return JSONResponse(
            {"error": {"message": f"model '{model_id}' not ready",
                       "code": "model_not_ready"}}, 503)
    if a_body.get("tools") and not _supports_tools(info):
        _METRICS["requests_error"] += 1
        return _tools_unsupported_error(model_id)
    cold = await cold_start_guard(info)
    if cold is not None:
        return cold

    oai = anth.to_openai(a_body)
    oai = prepare_chat(info, oai)
    # Honor the client's requested thinking level. Anthropic budget_tokens / effort
    # map to the model's native effort (gpt-oss: low/medium/high); inject it before
    # apply_thinking so the caller's level wins over the card default. Non-reasoning
    # cards (mode "none") simply answer without erroring.
    enabled, effort = anth.desired_thinking(a_body)
    pt_mode = ((info["card"].get("param_translation", {}) or {})
               .get("thinking", {}) or {}).get("mode", "none")
    if enabled and effort and pt_mode == "effort":
        oai["reasoning_effort"] = effort
    oai = apply_thinking(info["card"], oai, enabled)
    stream = bool(a_body.get("stream"))
    url = upstream_url("/v1/chat/completions")
    headers = upstream_headers(info)

    if stream and not info.get("no_stream"):
        oai["stream"] = True
        oai.setdefault("stream_options", {"include_usage": True})

        async def gen():
            yield b"".join(anth.stream_start_events(model_id))
            finish = None
            out_tokens = 0
            buf = ""
            t0 = time.monotonic()
            async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
                async with c.stream("POST", url, content=json.dumps(oai).encode(),
                                    headers=headers) as r:
                    async for chunk in r.aiter_text():
                        buf += chunk
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            obj = anth.parse_openai_sse_line(line)
                            if not obj:
                                continue
                            for ch in obj.get("choices", []) or []:
                                delta = (ch.get("delta") or {}).get("content")
                                if delta:
                                    yield anth.stream_delta_event(delta)
                                if ch.get("finish_reason"):
                                    finish = ch["finish_reason"]
                            u = obj.get("usage")
                            if u:
                                out_tokens = u.get("completion_tokens", out_tokens)
            latency_ms = int((time.monotonic() - t0) * 1000)
            for ev in anth.stream_stop_events(
                finish, out_tokens, resource_block(info, latency_ms)
            ):
                yield ev

        return StreamingResponse(
            gen(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    oai.pop("stream", None)
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as c:
        r = await c.post(url, content=json.dumps(oai).encode(), headers=headers)
    latency_ms = int((time.monotonic() - t0) * 1000)
    if r.status_code != 200:
        _METRICS["requests_error"] += 1
        return Response(content=r.content, status_code=r.status_code,
                        media_type=r.headers.get("content-type", "application/json"))
    out = anth.from_openai(r.json(), model_id)
    out["resources"] = resource_block(info, latency_ms)
    return JSONResponse(out)


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
    cold = await cold_start_guard(info)
    if cold is not None:
        return cold
    return await _forward(info, f"/v1/{path}", body, stream=False)


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
    return Response("\n".join(lines) + "\n", media_type="text/plain")
