# Inference Gateway — Architecture & Card Schema

> The **what and why**. For the build/deploy steps and current cluster state, see `RUNBOOK.md`.
> Supersedes the design notes in `GATEWAY-DESIGN.md` (kept for history).

## TL;DR

Cluster 230 needs a model inference gateway. The POC (232) proved the model serving stack
works but its gateway is **2072 lines with ~12 hardcoded dicts** and every new model means a
code change + redeploy. We replace that with a **card-driven gateway**: each model ships a
`details.yaml` ConfigMap, the gateway reads it, and adding a model is `kubectl apply` of two
files with zero gateway changes.

## Reality check (verified on the clusters, 2026-06-04)

| Fact | State | Implication |
|---|---|---|
| POC gateway reads cards? | **No** — `gateway.py` has zero card-loading code | The card system is *designed* but never built. We build it for real on 230. |
| Cards exist in git? | **Yes** — 157 models each have a `details.yaml` | We have real schema + real data to work from, not a blank page. |
| Card schema today | identity, deployment, routing, compatibility, meta_tasks, input_map, output_map, server_config | Already rich. We **extend**, not replace. |
| Cluster 230 stack | HAMi (40 vGPU), Tyk OSS+Redis, KServe, Knative, Istio all running; bge-small serving | Platform is ready; the gateway is the missing piece. |
| Cards deployed on 230 | **None** | Clean slate for the card namespace. |

## Architecture

```
api.vulcan.alliancecan.ca  (Traefik TLS)
        │
   Tyk OSS Gateway          (auth, rate limit, per-user analytics → Redis)
        │
        ▼
   model-gateway            (FastAPI Deployment in `models` ns, card-driven)
        │  reads details cards via K8s, applies defaults + param translation
        │
   per-PATH-FAMILY handlers (selected by URL path, NOT by card type):
     ├─ chat        /v1/chat/completions   → vLLM/llama.cpp (meta-tasks, thinking)
     ├─ anthropic   /v1/messages           → Anthropic ↔ OpenAI conversion
     ├─ embeddings  /v1/embeddings         → TEI ↔ OpenAI reshape
     ├─ rerank      /v1/rerank             → Cohere/Jina ↔ TEI
     ├─ audio       /v1/audio/{transcriptions,speech,voices,clone}
     │                                     → STT(multipart→json), TTS(json→bytes), clone
     ├─ vision      /v1/vision/{classify,embed,detect,segment,depth,face}
     │                                     → per-task default model, forward
     ├─ science     /v1/science/{predict,energy,splice,...}, /v1/design, /v1/dock
     │                                     → per-task default model, forward
     └─ forward     /v1/{custom}           → pass-through to model's own server.py
        │                                    (esmfold /v1/structure, etc.)
   knative-local-gateway → KServe InferenceService pods
```

Clean paths (no `/serving/` prefix from the POC):
`/v1/chat/completions`, `/v1/messages`, `/v1/embeddings`, `/v1/rerank`, `/v1/{custom}`.

Both protocols live under one `/v1/` namespace — `/v1/messages` is the Anthropic SDK's **native**
path and `/v1/chat/completions` is OpenAI's, so both official SDKs work by pointing at the domain
with no special prefix. The gateway dispatches by **path suffix** (unambiguous), never by sniffing
the request body.

## Why card-driven

The POC gateway encodes per-model behavior in code:

| Hardcoded dict (POC `gateway.py`) | Replaced by card field |
|---|---|
| `MODEL_MAX_TOKENS`, `CONTEXT_WINDOWS` | `max_completion_tokens`, `context_window` |
| `MODEL_TYPES` | `type` |
| `KSERVE_CUSTOM_MODELS`, `ISVC_NAME_MAP` | `routing.path_prefix`, `routing.k8s_name` |
| `REASONING_MODELS` | `param_translation.thinking` |
| `NO_STREAM_MODELS`, `SERIALIZED_MODELS` | `routing.no_stream`, `routing.serialize` |
| `TRUNCATION_LIMITS`, `startup_times` | `context_window`, `deployment.startup_seconds` |
| `EXTRA_MODELS`, `_CUSTOM_HEALTH_MODELS` | `deployment.*` (discovered, not listed) |

Result: the gateway has **no model names in code**. Behavior lives in data, owned by whoever
deploys the model.

## Card schema

Each model ships a ConfigMap labelled `model-details: "true"` in the `models` namespace,
holding a `details.json`. **The schema below = what exists today (kept) + what's new.**

### What already exists (157 cards have this — keep as-is)

```jsonc
{
  "id": "command-r-7b",
  "type": "chat",                     // chat | embedding | rerank | structure | ...
  "description_short": "...",
  "context_window": 8192,
  "max_completion_tokens": 4096,
  "endpoints": { "primary": "/v1/chat/completions", "health": "/v1/models" },

  "owned_by": "...", "source": "...", "license": "...",
  "parameters": "7B", "precision": "bfloat16", "framework": "vllm",

  "deployment": {
    "gpu": true, "gpu_count": 1, "gpu_type": "L40S",
    "min_replicas": 1, "max_replicas": 1,
    "startup_seconds": 120, "timeout": 600,
    "served_model_name": "command-r-7b"
  },
  "routing": {
    "path_prefix": "/v1/", "serialize": false, "no_stream": false,
    "deployment_mode": "Knative"
  },
  "compatibility": {
    "supports_streaming": true, "supports_vision": false, "supports_tools": true,
    "supports_system_prompt": true, "reasoning_model": false
  },
  "meta_tasks": {                     // OpenWebUI title/tags/followups caps
    "title":     {"max_tokens": 80},
    "tags":      {"max_tokens": 60},
    "followups": {"max_tokens": 220}
  },
  "input_map": { "...": "..." },      // documentation of accepted params
  "output_map": { "...": "..." },
  "server_config": { "cli_args": ["..."], "model_path": "/mnt/models" }
}
```

### What's NEW (the migration adds these)

This is the actual delta to land. Three additions:

```jsonc
{
  // 1. PARAM TRANSLATION — replaces REASONING_MODELS + per-model if/else.
  //    The gateway speaks ONE client dialect; the card maps it to the model's.
  "param_translation": {
    "thinking": {
      "mode": "toggle",               // toggle | effort | budget | always_on | none
      "on":  { "enable_thinking": true,  "chat_template_kwargs": {"enable_thinking": true} },
      "off": { "enable_thinking": false, "chat_template_kwargs": {"enable_thinking": false} },
      "budget_support": false
    },
    "max_tokens": { "field": "max_tokens" },   // null = model takes no max_tokens (science)
    "stop":       { "field": "stop" }
  },

  // 2. DEFAULTS — applied when the client omits a value. Card author knows the sweet spots.
  "defaults": {
    "chat": { "temperature": 0.6, "top_p": 0.95, "max_tokens": 4096,
              "thinking": {"enabled": true} },
    "meta_tasks": {                   // per-task thinking overrides live here now
      "title":     {"max_tokens": 80,  "thinking": {"enabled": false}},
      "tags":      {"max_tokens": 60,  "thinking": {"enabled": false}},
      "followups": {"max_tokens": 220, "thinking": {"enabled": false}}
    }
  },

  // 3. CUSTOM PARAMS — model-specific knobs, validated then passed through.
  "custom_params": {
    "schema": {
      "repetition_penalty": {"type": "float", "default": 1.1, "min": 0.9, "max": 2.0},
      "guided_json":        {"type": "string"}
    },
    "passthrough": true
  },

  "schema_version": 2                 // bump when the schema changes; gateway tolerates v1
}
```

### Trim the card — single source of truth

The existing 157 cards carry **too much data**: most fields either duplicate the K8s ISVC,
are queryable at runtime, or are pure catalog text the gateway never acts on. Rule:

> **The card holds ONLY what the gateway can't get anywhere else.**

| Bucket | Examples | Where it should live instead |
|---|---|---|
| Duplicates K8s ISVC/pod | `deployment.gpu*`, `container_image`, `node`, `served_model_name`, **all `server_config`** | the ISVC — gateway reads it live via Watch |
| Runtime-derivable | `context_window`, served name | vLLM `/v1/models` `max_model_len` when pod is up |
| Catalog / display only | `description`, `owned_by`, `license`, `precision`, `domain`, `tags`, `input_map`, `output_map` | optional `catalog` block (gateway ignores) or a `*-catalog` ConfigMap |

**The irreducible gateway card** (≈⅓ the current size — every field changes gateway behavior
and is non-derivable):

```jsonc
{
  "id": "qwen35-122b",
  "type": "chat",                                  // handler-class hint (else catalog-only)
  "endpoints": { "primary": "/v1/chat/completions" }, // custom path for science (e.g. /v1/structure)
  "routing":  {
    "k8s_name": "...",                             // only if ISVC name ≠ id
    "serialize": false, "no_stream": false,
    "upstream_model_id": null                      // e.g. "Systran/faster-whisper-large-v3"
  },
  "limits":   { "max_completion_tokens": 120000 }, // hard cap; context_window read at runtime
  "behavior": { "supports_vision": true, "supports_tools": true, "strips_thinking": true },
  "param_translation": { "thinking": { /* mode + on/off */ } },  // NOT derivable
  "defaults":          { "chat": {/*...*/}, "meta_tasks": {/*...*/} },
  "custom_params":     { "schema": {/*...*/}, "passthrough": true },
  "schema_version": 2
  // optional: "catalog": { description, license, tags, domain, parameters, ... }  ← gateway ignores
}
```

For **science / custom-server models**, the core shrinks further — no thinking, no chat defaults:
`id`, `type`, `endpoints.primary` (the custom path), `routing`, `limits` (often `max_completion_tokens: 0`),
and `custom_params` for input validation. Everything else is catalog.

Anything the gateway reads for **usage logging** (gpu_type, vram, node, replicas) comes from
the **pod resource requests + node status** it already watches — not from the card. One fact,
one source.

### Thinking modes (the one genuinely tricky bit)

`param_translation.thinking.mode` drives all reasoning behavior:

| mode | meaning | example model | `on` injects |
|---|---|---|---|
| `toggle` | on/off via param | qwen35-122b | `enable_thinking: true` |
| `effort` | qualitative levels | gpt-oss-120b | `reasoning_effort: "medium"` |
| `budget` | exact token budget | (Anthropic-native) | `thinking.budget_tokens` |
| `always_on` | can't disable (launched with `--enable-reasoning`) | phi-4-reasoning | nothing |
| `none` | no reasoning | command-r-7b | nothing |

`always_on` models get **higher** meta-task caps — they will think regardless, so the tokens burn.

## Discovery — ConfigMaps + K8s Watches

- On startup: one-time `list` of InferenceServices + `model-details` ConfigMaps to seed the table.
- Then: K8s **Watch** on both. `kubectl apply` of a card → routing table updates in milliseconds,
  no restart, no polling. (The POC's "60s poll" is what we're replacing — don't reintroduce it.)
- Card is the **base** (works even when a model is scaled to zero). Live runtime data
  (`/v1/models`, `/health`, `/info`) **supplements** when the pod is up.

| Source | Provides | Available |
|---|---|---|
| ConfigMap card | type, context, defaults, param_translation, endpoints | always |
| ISVC (K8s API) | host, ready, replicas, node | always |
| Model `/v1/models` (vLLM) | real `max_model_len`, served name | pod running |
| Model `/health` (custom) | loaded state, device | pod running |

## Gateway request flow

```
1. Resolve model → find card
2. Apply card defaults for anything the client didn't set
3. Detect meta-task (title/tags/followups) → apply defaults.meta_tasks overrides
4. Translate params via param_translation (thinking → model dialect)
5. Validate custom_params against schema
6. Cap max_tokens to max_completion_tokens; truncate input to context_window
7. Route to handler (chat/embedding/rerank/anthropic/forward)
8. Forward via knative-local-gateway; stream back with backpressure
```

### Honest caveat on "no response stripping"

The POC has `_strip_thinking`, `_fix_title_response`, etc. The *goal* is that correct params
yield clean output and these become unnecessary. Treat that as a goal, **not a guarantee** —
keep a thin, card-gated post-processor (`compatibility.strips_thinking`) as a fallback. Some
models emit `<think>` blocks no matter what you send.

## Handlers are per-path-family, not per-type (lesson from the POC)

The POC gateway dispatches on the **URL path family**, and there are far more families than the
"chat/embedding/rerank" core. These are all real, with distinct content handling. **Keep them.**

| Path family | Content | Gateway does | Example models |
|---|---|---|---|
| `/v1/chat/completions` | JSON | defaults + thinking + meta-tasks | qwen35-122b, command-r-7b |
| `/v1/messages` | JSON | Anthropic→OpenAI→pipeline→back | (same chat backends) |
| `/v1/embeddings` | JSON | TEI ↔ OpenAI reshape | bge-m3, esm2, dnabert-s |
| `/v1/rerank` | JSON | Cohere/Jina ↔ TEI | bge-reranker-v2-m3 |
| `/v1/audio/transcriptions` | **multipart → JSON** | STT; **HF model-ID remap** (whisper→`Systran/…`) | whisper-large-v3 |
| `/v1/audio/speech` | **JSON → raw audio bytes** | TTS; kokoro ID remap | kokoro-82m |
| `/v1/audio/voices`, `/v1/audio/clone` | mixed | XTTS voice cloning | xtts-v2 |
| `/v1/vision/{classify,embed,detect,segment,depth,face}` | JSON | **per-task default model**, forward | yolov8s, dino-vit-b8, depth-anything-v2 |
| `/v1/science/{predict,energy,splice,…}`, `/v1/design`, `/v1/dock` | JSON | per-task default, forward | chgnet, splicebert, proteinmpnn, diffdock |
| `/v1/{custom}` (e.g. `/v1/structure`) | JSON | **forward to the model's own `server.py`** | esmfold, alphafold2, boltz-1 |

### `type` is a catalog label, not a handler selector

The cards carry ~23 `type` values (`chat`, `embedding`, `embed`, `forecast`, `classify`,
`structure`, `force-field`, `dock`, `design`, `3d`, `segment`, `detect`, `ocr`, …). These are
**mostly catalog metadata** for `/v1/models` and a future model-listing UI — the POC comment is
explicit: *"anything not listed defaults to chat."* The gateway picks a **handler from the path**,
not from `type`. Implications:

- `type` belongs to the optional **catalog** block for most models, not the gateway-critical core.
- The gateway-critical signal is the model's **endpoint path** + a coarse handler class. Keep
  `type` only where it changes behavior (e.g. distinguishing OpenAI-`embedding` reshaping from a
  custom `embed` model that's just forwarded).
- `/v1/models` filtering: only chat-class models surface to OpenWebUI's model picker; everything
  else is still discoverable but not shown as a chat model.

### Science / custom models = forward to their own server

Science models ship a custom **`server.py`** (FastAPI) that exposes its own endpoint
(`esmfold` → `/v1/structure`, `/health`, `/v1/models`). The gateway does **not** reshape these —
it **forwards**. So the trimmed card must still carry the model's **custom endpoint path** and any
**per-task default-model** mapping; that's gateway-relevant routing, not catalog text. The
boltz-1 card, for example, declares `/v1/science/predict` — keep that.

### Phase-1 implications (don't lose these to the "clean core")

- Non-JSON content paths are mandatory: **multipart** (STT) and **raw-bytes responses** (TTS).
- **Per-task default models**: `/v1/vision/detect` → yolov8s when the client names no model.
- **Upstream model-ID remapping**: some backends need full HF ids (whisper, kokoro). Put the map
  in the card (`routing.upstream_model_id`) instead of a hardcoded dict.
- The `/v1/{custom}` **catch-all forwarder** is first-class — register it last, after the known paths.

## Dual protocol: OpenAI + Anthropic — what's actually supported

**The backend is vLLM's OpenAI-compatible server (+ TEI for embeddings).** That single fact
defines the limits:

- **OpenAI Chat Completions is native** — vLLM speaks it directly.
- **Anthropic is gateway-side translation only**: Anthropic → OpenAI → vLLM, and back.
  It can expose a feature only if it exists in *both* the Anthropic spec *and* vLLM.

So we do **not** support "all features for both." We support a **common chat core** that maps
cleanly, and we explicitly **drop or reject** provider-specific features that have no backend.
Promising full parity would be writing checks vLLM can't cash.

### Parity matrix (verified against live OpenAI + Anthropic specs, 2026-06-04)

| Capability | OpenAI | Anthropic | Support |
|---|---|---|---|
| Messages / multi-turn | `messages[]` | `messages[]` | ✅ full |
| System prompt | `system`/`developer` role | top-level `system` | ✅ full (relocate) |
| Max output tokens | `max_completion_tokens` | `max_tokens` (**required**) | ✅ full (inject default if Anthropic omits) |
| Sampling | `temperature`, `top_p` | `temperature`, `top_p` | ✅ full |
| `top_k` | — (vLLM extension) | `top_k` | ✅ via vLLM |
| Stop sequences | `stop` | `stop_sequences` | ✅ full |
| Streaming | `chat.completion.chunk` SSE | `message_delta` SSE events | ✅ full (re-shape events) |
| Vision (image **input**) | `image_url` part | `image` block | ✅ if `compatibility.supports_vision` |
| Tools (client) | `tools[].function` | `tools[].input_schema` | ✅ core |
| Tool choice | `auto/required/none/{name}` | `auto/any/none/{tool}` | ✅ full mapping |
| Parallel tools | `parallel_tool_calls` | `disable_parallel_tool_use` | ✅ inverted bool |
| **Thinking — effort** | `reasoning_effort` | `output_config.effort` (low/med/high/xhigh/max) | ✅ **direct** effort↔effort (card `mode: effort`) |
| **Thinking — budget** | — | `thinking.budget_tokens` | ⚠️ lossy fallback → bucketed to effort/toggle |
| Structured output | `response_format.json_schema` | `output_config.format` | ⚠️ via vLLM `guided_json`, model-dependent |
| logprobs | `logprobs`/`top_logprobs` | — | ⚠️ only if model enables |
| `n > 1` | `n` | — | ⚠️ model-dependent |
| Prompt caching | — | `cache_control` | ❌ drop (no backend) |
| Citations / documents | — | `citations`, `document` blocks | ❌ drop |
| Server tools (web/code) | — | `web_search`, `code_execution`, `bash` | ❌ 400 (no backend) |
| Multi-turn thinking signatures | — | `redacted_thinking`, `signature` | ❌ drop |
| Audio in/out | `modalities:["audio"]` | — | ❌ drop |
| Moderation / `service_tier` | both have variants | both have variants | ❌ ignore |

Legend: ✅ full · ⚠️ partial/model-dependent · ❌ unsupported (drop silently, or 400 for
server-side tools so callers aren't surprised).

### Thinking translation — mostly clean now, lossy only for budget

Anthropic added **`output_config.effort`** (low/medium/high/xhigh/max), so the common case is a
**direct effort↔effort mapping** with OpenAI `reasoning_effort` and gpt-oss's own levels. The
old budget heuristic is now only a fallback for clients that send `thinking.budget_tokens`.

```
client thinking ──(card param_translation.thinking.mode)──> model dialect
   mode: effort     → effort↔effort DIRECT (OpenAI reasoning_effort / Anthropic output_config.effort)
                      budget_tokens (if sent instead) → bucket: <2k→low, <8k→medium, else high
   mode: toggle     → map effort/budget → on/off (enable_thinking + chat_template_kwargs)
   mode: budget     → pass budget through (rare; only if model truly honors a token budget)
   mode: always_on  → ignore (model always thinks)
   mode: none       → strip thinking entirely
```

Only `budget_tokens → toggle/effort` is lossy. effort↔effort and budget-native are exact.

### Our OpenAI extensions (the POC added these — keep them, card-driven)

The gateway speaks OpenAI **plus** a few non-standard fields. These are not invented per request —
they're produced by the card's `param_translation` / `custom_params`, so they stay data-driven:

| Extension | Where | Purpose | Card source |
|---|---|---|---|
| `enable_thinking` (req) | chat body | toggle reasoning on vLLM | `param_translation.thinking.on/off` |
| `chat_template_kwargs` (req) | chat body | vLLM chat-template passthrough | `param_translation.thinking.on/off` |
| `top_k`, `repetition_penalty`, `guided_json`, `guided_regex` (req) | chat body | vLLM sampling / structured output | `custom_params.schema` + `passthrough` |
| `reasoning_content` / `reasoning` (resp) | chat response | gpt-oss returns answer in `reasoning` w/ `content=null` — gateway normalizes | handler logic (universal) |
| `/v1/rerank` | endpoint | Cohere/Jina rerank → TEI `{query,texts}` | path-family handler |

So "OpenAI-compatible" here means **OpenAI core + these documented extensions**, all expressible
in the card — no per-model code.

### Endpoint surface

| Path | Protocol | Notes |
|---|---|---|
| `/v1/chat/completions` | OpenAI | native, full core |
| `/v1/embeddings` | OpenAI | TEI ↔ OpenAI reshape |
| `/v1/rerank` | Cohere/Jina | TEI rerank |
| `/v1/models` | OpenAI | discovery list from cards |
| `/v1/messages` | Anthropic | native Anthropic SDK path; translation layer, common core only |

> **Routing order:** register the known paths (`/v1/chat/completions`, `/v1/messages`,
> `/v1/embeddings`, `/v1/rerank`, `/v1/models`) **before** the `/v1/{custom}` catch-all so
> FastAPI matches them first. Reserve those names — a model can't claim a custom `/v1/messages`.

### Build implication

The Anthropic endpoint is **one translation module**, not a parallel implementation. It
converts request → OpenAI shape, runs the *same* card pipeline (defaults, param_translation,
routing), then converts the response + SSE events back to Anthropic shape. Build the OpenAI
path first (Phase 1); add the Anthropic translator as a thin wrapper once chat is solid.
Unsupported Anthropic fields are dropped on input; server-side tool requests get a `400`.

## Open questions (decide before/while building)

1. **`schema_version`** — adopt now (answer: yes; gateway must read v1 cards too during migration).
2. **Streaming thinking tokens** — add `param_translation.thinking.streams_thinking` when needed.
3. **custom_params strictness** — reject invalid, or warn + pass through? (Lean: reject on type, warn on range.)
4. **Tool-call format** — Qwen=Hermes vs native OpenAI → `compatibility.tool_format` if it bites.

Defer 2–4 until a model actually needs them. Don't pre-build.
