# Aleph Model Gateway

Card-driven FastAPI inference gateway for the HAMI Kubernetes cluster. Routes requests to KServe InferenceServices through a single `/v1/` endpoint, supporting both OpenAI and Anthropic API formats.

## Architecture

```
Client → Tyk (auth, rate-limit) → model-gateway (FastAPI :8080)
                                          │
            ┌─────────────────────────────┼──────────────────────────────┐
            ↓                             ↓                              ↓
    /v1/chat/completions          /v1/embeddings              /v1/science/*
    /v1/messages                  /v1/rerank                  /v1/vision/*
            │                             │                              │
            ↓                             ↓                              ↓
    vLLM pods (LLMs)              TEI/custom pods         Custom FastAPI pods
    (via Knative local GW)        (via Knative local GW)  (via Knative local GW)
```

**No model names are hardcoded.** The gateway discovers models at runtime from `details.yaml` ConfigMaps (label `model-details=true`) and live InferenceService state via the Kubernetes API.

## API Standards

The gateway speaks four API formats depending on the endpoint:

| Endpoint | Standard | Who defined it | Models |
|---|---|---|---|
| `/v1/chat/completions` | OpenAI Chat | OpenAI | ~30 LLMs |
| `/v1/messages` | Anthropic Messages | Anthropic | Same ~30 LLMs (translated internally) |
| `/v1/embeddings` | OpenAI Embeddings | OpenAI | ~50 embedding models |
| `/v1/rerank` | Cohere Rerank v2 | Cohere | 1 model (bge-reranker-v2-m3) |
| `/v1/science/*`, `/v1/vision/*`, etc. | Custom | Us | ~60 science + vision models |

### OpenAI vs Anthropic field mapping

The gateway translates between OpenAI and Anthropic formats inline in `gateway.py` (functions prefixed `anth_`). Here are the key differences:

| Concept | OpenAI (`/v1/chat/completions`) | Anthropic (`/v1/messages`) | Translation |
|---|---|---|---|
| System prompt | `messages[0].role == "system"` | Top-level `system` field | Prepended; extra system/developer messages folded to the front (Qwen chat-template) |
| Message roles | system, user, assistant, tool | user, assistant only | Tool results → text blocks |
| Tools | `{type:"function", function:{name,desc,parameters}}` | `{name, description, input_schema}` | Wrap/unwrap nesting |
| Tool choice | "auto", "none", "required" | `{type:"auto"|"any"|"tool"|"none"}` | `"any"` → `"required"` |
| Stop sequences | `stop` field | `stop_sequences` field | Rename |
| Max tokens | Optional | **Required** | Inject default from card |
| Thinking | `reasoning_effort` string | `thinking.budget_tokens` int | Via card `param_translation.thinking` |
| Streaming | `data: {json}\n\n` + `[DONE]` | Typed SSE events (`event: message_start`) | Full format conversion |
| Images | `{type:"image_url", image_url:{url}}` | `{type:"image", source:{type:"base64"}}` | Convert base64 URL |
| Finish reasons | stop, length, tool_calls | end_turn, max_tokens, tool_use | `_STOP_MAP` lookup |
| Response content | `choices[0].message.content` (string) | `content` (array of typed blocks) | Wrap/unwrap |

### Which models support which API

Only **chat-type LLMs** support the Anthropic Messages API. Everything else is OpenAI-standard or custom:

| Model type | `/v1/chat/completions` | `/v1/messages` |
|---|---|---|
| Chat LLMs (gpt-oss, qwen, gemma, deepseek, etc.) | ✅ | ✅ |
| Reasoning LLMs (phi-4, r1-distill, qwq) | ✅ | ✅ |
| Embedding models | ✅ `/v1/embeddings` | ❌ |
| Science models | ✅ `/v1/science/*` | ❌ |
| Rerankers | ✅ `/v1/rerank` | ❌ |
| Vision models | ✅ `/v1/vision/*` | ❌ |
| TTS/STT | ✅ `/v1/audio/*` | ❌ |
| Image generation | ✅ `/v1/images/*` | ❌ |

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /v1/models` | GET | Model catalog (`?all=true` for non-chat). Anthropic surface (`X-Aleph-Api: anthropic` or `anthropic-version`) returns always-on chat models in Anthropic list shape. |
| `POST /v1/chat/completions` | POST | OpenAI chat (streaming supported) |
| `POST /v1/messages` | POST | Anthropic Messages (streaming supported) |
| `POST /v1/messages/count_tokens` | POST | Anthropic token count (forwards to vLLM; does not strip `model`) |
| `POST /v1/embeddings` | POST | Embeddings (OpenAI format) |
| `POST /v1/rerank` | POST | Reranking (Cohere v2 → TEI translation) |
| `POST /v1/science/*` | POST | Science model catch-all (predict, forecast, embed, etc.) |
| `POST /v1/vision/*` | POST | Vision tasks (classify, detect, segment, depth, embed, face) |
| `POST /v1/audio/speech` | POST | Text-to-speech |
| `POST /v1/audio/transcriptions` | POST | Speech-to-text |
| `POST /v1/images/generations` | POST | Text-to-image |
| `POST /v1/dock` | POST | Molecular docking |
| `POST /v1/design` | POST | Protein design |
| `POST /v1/structure` | POST | Protein structure prediction |
| `POST /v1/forecast` | POST | Time-series forecasting |
| `POST /v1/translate` | POST | Translation |
| `POST /v1/detect` | POST | Detection |
| `GET /healthz` | GET | Health check |
| `GET /readyz` | GET | Readiness (cards loaded) |
| `GET /metrics` | GET | Prometheus metrics (cluster-wide fan-in; `?local=true` for this replica) |

Public Anthropic/Claude Code URL: `https://inference.vulcan.alliancecan.ca/anthropic` (Tyk strips `/anthropic` and injects `X-Aleph-Api: anthropic`). Direct `/v1/messages` still works.

## Card-driven discovery

Models declare themselves via `details.yaml` ConfigMaps in the `models` namespace:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpt-oss-120b-details
  namespace: models
  labels:
    model-details: "true"     # ← gateway watches this label
data:
  details.json: |
    { "id": "gpt-oss-120b", ... }
```

The gateway:
1. **Seeds** on startup — lists all ConfigMaps with `model-details=true`, parses `details.json`
2. **Watches** — K8s watch stream for ConfigMap ADD/MODIFY/DELETE events
3. **Merges** with live ISVC state — readiness, replica counts, resource allocation

### Fields the gateway reads from details.yaml

| Field path | What the gateway uses it for |
|---|---|
| `routing.k8s_name` | Maps model ID → ISVC name (if different) |
| `routing.upstream_model_id` | Rewrites `model` field for backends expecting a different name |
| `routing.no_stream` | Disables streaming for models that can't handle it |
| `behavior.supports_tools` | Gates tool calling (400 if tools sent to unsupported model) |
| `behavior.strips_thinking` | Strips reasoning content from responses |
| `behavior.reasoning_model` | Enables reasoning-specific logic (auto-skip on low budget) |
| `behavior.supports_vision` | Advertises vision in model catalog |
| `param_translation.thinking.*` | Maps effort levels → `thinking_token_budget` or `reasoning_effort` |
| `defaults.chat.*` | Auto-applies default temperature, max_tokens, thinking |
| `defaults.meta_tasks.*` | Overrides for OpenWebUI title/tags/followup tasks |
| `scaling.scale_to_zero` | Enables cold-start guard (wake-up + 503) |
| `scaling.cold_start_estimate` | ETA in the 503 retry message |
| `limits.context_window` | Hard cap on context |
| `limits.max_completion_tokens` | Hard cap on output tokens |

## Scale-to-zero

When a model is scaled to zero (minReplicas=0), the gateway:

1. Detects 0 ready replicas for the model's active revision
2. Fires an async wake-up request to nudge Knative's activator
3. Returns HTTP 503 with `Retry-After: 30` and an ETA from the card's `cold_start_estimate`
4. Client retries → model is now warming up → eventually serves

## Usage accounting & identity

Every served request (and every cold-start event) is written as one JSON line to
an in-pod log for fairshare/billing. The log is an `emptyDir` at
`GATEWAY_USAGE_LOG` (default `/var/log/aleph/usage.log`), kept separate from app
stdout and intentionally not mounted to the host — ship it out of band
(promtail/fluent-bit) later.

```bash
kubectl exec -n models deploy/model-gateway -c gateway -- tail -f /var/log/aleph/usage.log
```

Each record carries: `identity`/`account`/`identity_type`, `model`, `api`,
`endpoint`, `status`, `latency_ms`, `cold_start`, `tokens` (normalized
prompt/completion/total plus `detail` = the verbatim vLLM `usage`, so
reasoning/cached token breakdowns are preserved when present), `context_window`,
`max_completion_tokens`, a `resources` block (gpus, vram_mib, cpu_cores,
system_ram_mib, **gpu_product**, **node**), and derived `gpu_seconds`. Per-model
rollups are exposed on `/metrics`.

**Where the compute facts come from:**
- gpus/vram_mib/cpu_cores/system_ram_mib — the model's ISVC predictor `resources`.
- gpu_product/node — the gateway resolves `model → predictor pod → node` (K8s
  watches) and reads the node's `aleph.gpu/product` label, stamped by the
  `node-labeler` DaemonSet (`11-node-labeler.yaml`).

**Identity** is set by Tyk and read from request headers
(`X-Aleph-Identity`/`-Account`/`-Identity-Type`). Requests that don't pass through
Tyk are logged as `anonymous`. See `gateway/tyk/` and `tyk-admin.sh` (on PATH on control-plane nodes).

### API key acceptance (catch-all)

Tyk's `normalizeAuth` pre-hook (`gateway/tyk/middleware/`) accepts the API key
under any common convention and normalizes it to `Authorization: Bearer`:

- `Authorization: Bearer <key>` (OpenAI/Cohere) or raw `Authorization: <key>`
- `x-api-key: <key>` (Anthropic)
- `api-key: <key>` (Azure OpenAI)
- `x-goog-api-key: <key>` (Google)
- `?api_key=` / `?api-key=` / `?key=` query string

### Key administration (control plane)

`tyk-admin.sh` is baked onto control-plane nodes at `/usr/local/bin` (on PATH;
source: `ww-overlays/overlays/control-plane/usr/local/bin/tyk-admin.sh`). It reads
the APISecret from the in-cluster Secret, auto-discovers the Tyk endpoint, and
writes an audit log:

```bash
KEY=$(tyk-admin.sh add-user openwebui shared-pool service)  # prints key
tyk-admin.sh validate-key openwebui "$KEY"                  # true/false
tyk-admin.sh update-user openwebui                          # rotate key
tyk-admin.sh invalidate-key "$KEY"
```

Identity lives in the key's **alias** (identity) + **tags**
(`account:<x>`, `type:<service|user>`) — Tyk OSS wipes `meta_data` on first
request, so we don't depend on it.

## CI/CD

```mermaid
main push (gateway/**) → GitHub Actions → Docker build → Docker Hub push
    Image: rkhoja/aleph:latest
    Image: rkhoja/aleph:gateway-<sha>
```

**Workflow:** `.github/workflows/deploy-gateway.yml`
- Triggers on `main` push touching `gateway/**`
- Builds from `gateway/Dockerfile`
- Pushes two tags: `latest` (rolling) and `gateway-<shortsha>` (immutable)
- Manual trigger via `workflow_dispatch` with custom tag override

## Deploy

The gateway, Tyk, and all supporting resources deploy as RKE2 auto-deploy
manifests via the Warewulf overlay (`ww-overlays/`) — there is no deploy script.
The live Deployment is **pinned** to an immutable `rkhoja/aleph:gateway-<sha>`
tag in `63-model-gateway.yaml` (`imagePullPolicy: IfNotPresent`). After CI:

```bash
# Pin the new immutable build (also bump the tag in 63-model-gateway.yaml)
sudo ssh root@<control-plane> "kubectl set image deploy/model-gateway -n models gateway=rkhoja/aleph:gateway-<sha>"
```

A rebuild resurrects whatever tag is pinned in the overlay — never leave live
on `:latest`.

## Key files

| File | Purpose |
|---|---|
| `app/gateway.py` | Main FastAPI app: discovery, routing, endpoints, Anthropic translation, scale-to-zero |
| `cards/*.yaml` | Gateway-side model cards (most live in per-model dirs) |
| `k8s/deployment.yaml` | Gateway Deployment (runs on control-plane, no GPUs) |
| `k8s/rbac.yaml` | ServiceAccount + RBAC for ConfigMap/ISVC reads |
| `k8s/service.yaml` | ClusterIP Service |
| `tyk/*.json` | Tyk API gateway config |
| `Dockerfile` | Python 3.11 slim + FastAPI |
| `requirements.txt` | FastAPI, httpx, kubernetes client |

## Why not LiteLLM?

LiteLLM normalizes 100+ LLM provider APIs into one interface. We considered it but decided against it:

1. **We already translate** — the Anthropic↔OpenAI translation is built into `gateway.py`, which is the only translation we need
2. **LiteLLM doesn't do K8s** — It can't discover models from ConfigMaps, handle scale-to-zero, apply per-card thinking defaults, gate tool support, or track resource usage
3. **All models are on-cluster** — LiteLLM shines when routing to cloud APIs (Bedrock, Azure, Vertex). Our models run locally via vLLM or custom servers
4. **Extra hop** — Adding LiteLLM means client → gateway → LiteLLM → vLLM. More latency, more failure modes
5. **No science model support** — LiteLLM only understands chat/embedding APIs, not our `/v1/science/*` models

**Revisit if:** we start routing to cloud APIs, or need Google Gemini / Cohere / Mistral format support.
