# Inference Gateway Design — HAMI Cluster (172.26.92.230)

> Design doc for the new model inference gateway.  
> Builds on POC design at `/root/kuberflow-working/MODEL-DETAILS-SYSTEM.md` on 172.26.92.232.  
> This doc captures what the POC got wrong and what we're changing.

## Architecture

```
api.vulcan.alliancecan.ca (TLS via Traefik)
         │
      Tyk OSS Gateway (auth, rate limiting, accounting)
         │
         ▼
   model-gateway (FastAPI, reads details cards)
         │
      per-TYPE handlers:
      ├─ chat:      forward to vLLM/llama.cpp, handle meta-tasks, manage thinking
      ├─ embedding: reshape TEI ↔ OpenAI format
      ├─ anthropic: Anthropic protocol ↔ OpenAI conversion
      ├─ reranker:  Cohere/Jina format ↔ TEI format
      └─ default:   forward as-is (science models normalize their own APIs via server.py)
         │
      knative-local-gateway → KServe InferenceService pods
```

**Key change from POC**: No `/serving/` prefix. Clean API paths:
- `/v1/chat/completions` — OpenAI-compatible chat
- `/v1/embeddings` — OpenAI-compatible embeddings
- `/v1/rerank` — Cohere/Jina-compatible reranking
- `/anthropic/v1/messages` — Anthropic-compatible messages
- `/v1/{custom}` — model-specific endpoints (structure, detect, etc.)

**External domain**: `api.vulcan.alliancecan.ca` (not `inference.kubeflow.vulcan.alliancecan.ca`)

## What the POC Got Wrong

### 1. Hardcoded dicts (300+ lines of per-model config in gateway.py)

The POC gateway has **8 hardcoded dicts** mapping model names to behavior:

| Dict | Lines | Purpose |
|---|---|---|
| `MODEL_MAX_TOKENS` | ~20 | Per-model output token caps |
| `CONTEXT_WINDOWS` | ~25 | Per-model context sizes |
| `MODEL_TYPES` | ~35 | Per-model type (chat/embedding/structure/etc) |
| `KSERVE_CUSTOM_MODELS` | ~40 | Which models use `/v1/` vs `/openai/v1/` |
| `ISVC_NAME_MAP` | ~20 | k8s ISVC name → API name mapping |
| `REASONING_MODELS` | ~5 | Which models have thinking mode |
| `NO_STREAM_MODELS` | ~3 | Models where streaming is disabled |
| `SERIALIZED_MODELS` | ~3 | Single-worker models needing request queueing |
| `TRUNCATION_LIMITS` | ~3 | Input truncation thresholds |
| `startup_times` | ~15 | Per-model cold-start estimates |
| `_CUSTOM_HEALTH_MODELS` | ~7 | Models needing /health probes |
| `EXTRA_MODELS` | ~5 | Non-KServe backend URLs |

Every new model = gateway code change + redeploy. The new gateway reads all of this from details cards.

### 2. Meta-task handling is fragile

The gateway sniffs prompt text to detect OpenWebUI title/tags/follow-up requests, then applies different token caps and thinking settings per model. The caps are hardcoded with `is_reasoning` branches. This should be in the card.

### 3. No standardized param translation

Every model family speaks a different dialect for thinking/reasoning, but the gateway has per-model `if` statements instead of a translation layer. The card should declare how to translate.

### 4. Response stripping hacks

The gateway has `_strip_thinking()`, `_fix_title_response()`, `_fix_tags_response()`, `_fix_followups_response()` — regex-based post-processing to clean up model output. These exist because the wrong params were sent to the model. If the card maps params correctly, the model outputs clean responses.

## Details Card Design

Each model ships a `details.yaml` ConfigMap (label `model-details: "true"`). The gateway reads all cards during discovery. Adding a model = deploy ISVC + card, zero gateway changes.

### Card Schema

Three sections: **identity**, **translation**, **defaults**.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: <model>-details
  namespace: models
  labels:
    model-details: "true"
data:
  details.json: |
    {
      // ── IDENTITY (required) ──
      "id": "qwen3-235b",
      "type": "chat",
      "description_short": "Qwen3 235B MoE, reasoning + tool use",
      "context_window": 131072,
      "max_completion_tokens": 121000,
      "endpoints": {
        "primary": "/v1/chat/completions",
        "health": "/v1/models"
      },

      // ── PROVENANCE ──
      "owned_by": "Qwen",
      "source": "BAAI/bge-m3",
      "license": "Apache-2.0",
      "parameters": "235B total / 22B active",
      "framework": "vllm",
      "precision": "awq-int4",

      // ── DEPLOYMENT (replaces startup_times, _CUSTOM_HEALTH_MODELS, etc) ──
      "deployment": {
        "gpu": true,
        "gpu_count": 4,
        "gpu_type": "L40S",
        "min_replicas": 1,
        "max_replicas": 1,
        "startup_seconds": 300,
        "serialize": false,          // replaces SERIALIZED_MODELS
        "custom_health": false       // replaces _CUSTOM_HEALTH_MODELS
      },

      // ── ROUTING (replaces KSERVE_CUSTOM_MODELS, ISVC_NAME_MAP) ──
      "routing": {
        "path_prefix": "/v1/",
        "k8s_name": "qwen3-235b",    // ISVC name if different from API id
        "no_stream": false            // replaces NO_STREAM_MODELS
      },

      // ── COMPATIBILITY (replaces REASONING_MODELS etc) ──
      "compatibility": {
        "supports_streaming": true,
        "supports_vision": false,
        "supports_tools": true,
        "supports_system_prompt": true
      },

      // ── PARAM TRANSLATION (NEW — not in POC) ──
      // Maps standardized client params to model-specific params.
      // The gateway receives one format, translates via this map.
      "param_translation": {
        "thinking": {
          // How to translate "thinking" to this model's dialect.
          // Modes: "toggle" (on/off), "effort" (qualitative levels),
          //        "budget" (exact token budget), "always_on", "none"
          "mode": "toggle",
          // When client sends thinking: true, these params get injected:
          "on": {
            "enable_thinking": true,
            "chat_template_kwargs": {"enable_thinking": true}
          },
          // When client sends thinking: false (or meta-task auto-disable):
          "off": {
            "enable_thinking": false,
            "chat_template_kwargs": {"enable_thinking": false}
          },
          // Does this model support thinking budget (exact token count)?
          "budget_support": false
        },
        "max_tokens": {
          // Where to put the max_tokens value in the request.
          // Most models use "max_tokens" directly.
          "field": "max_tokens"
        },
        "stop": {
          // Where to put stop sequences.
          "field": "stop"
        }
      },

      // ── DEFAULTS (NEW — not in POC) ──
      // Applied when client doesn't specify. Card author knows model's sweet spots.
      "defaults": {
        "chat": {
          "temperature": 0.6,
          "top_p": 0.95,
          "top_k": 20,
          "max_tokens": 4096,
          "thinking": {
            "enabled": true,
            "budget_tokens": null     // null = no budget limit, use model default
          }
        },
        "meta_tasks": {
          // Token caps and thinking overrides for OpenWebUI meta-tasks.
          // Reasoning models need higher caps (they think then answer).
          // Non-reasoning models get lower caps (direct answer).
          "title":    {"max_tokens": 80,  "thinking": {"enabled": false}},
          "tags":     {"max_tokens": 60,  "thinking": {"enabled": false}},
          "followups": {"max_tokens": 220, "thinking": {"enabled": false}}
        }
      },

      // ── CUSTOM PARAMS (NEW — not in POC) ──
      // Model-specific params the gateway doesn't understand.
      // Validated against schema, then passed through blindly.
      "custom_params": {
        "schema": {
          "repetition_penalty": {"type": "float", "default": 1.1, "min": 0.9, "max": 2.0},
          "top_k": {"type": "integer", "default": 20, "min": 1, "max": 100},
          "guided_json": {"type": "string", "description": "JSON schema for structured output"},
          "guided_regex": {"type": "string", "description": "Regex for constrained generation"}
        },
        "passthrough": true
      },

      // ── DISCOVERY ──
      "domain": "nlp",
      "subdomain": "large-language-model",
      "tags": ["chat", "llm", "reasoning", "moe"],
      "tier": "production",

      // ── INPUT/OUTPUT MAPS ──
      "input_map": {
        "messages": {"type": "array", "required": true},
        "max_tokens": {"type": "integer", "default": 4096, "max": 121000}
      },
      "output_map": {
        "choices": {"type": "array"},
        "usage": {"prompt_tokens": "int", "completion_tokens": "int"}
      }
    }
```

### Card examples for different thinking modes

**phi-4-reasoning** (always-on thinking, can't disable):
```json
"param_translation": {
  "thinking": {
    "mode": "always_on",
    "budget_support": false,
    "note": "vLLM launched with --enable-reasoning, can't disable per-request"
  }
},
"defaults": {
  "chat": {
    "max_tokens": 4096,
    "thinking": {"enabled": true, "mode": "always_on"}
  },
  "meta_tasks": {
    "title":    {"max_tokens": 500},
    "tags":     {"max_tokens": 400},
    "followups": {"max_tokens": 800}
  }
}
```
Higher meta-task caps because thinking can't be turned off — the model WILL think, those tokens WILL burn.

**GPT-OSS-120B** (effort-based reasoning):
```json
"param_translation": {
  "thinking": {
    "mode": "effort",
    "effort_levels": ["none", "minimal", "low", "medium", "high", "xhigh"],
    "on":  {"reasoning_effort": "medium"},
    "off": {"reasoning_effort": "none"},
    "effort_map": {
      "low": "low",
      "medium": "medium",
      "high": "high"
    }
  }
},
"defaults": {
  "chat": {
    "max_tokens": 4096,
    "thinking": {"enabled": true, "effort": "medium"}
  },
  "meta_tasks": {
    "title":    {"max_tokens": 80,  "thinking": {"enabled": true, "effort": "none"}},
    "tags":     {"max_tokens": 60,  "thinking": {"enabled": true, "effort": "none"}},
    "followups": {"max_tokens": 220, "thinking": {"enabled": true, "effort": "none"}}
  }
}
```

**command-r-7b** (no thinking):
```json
"param_translation": {
  "thinking": {
    "mode": "none"
  }
},
"defaults": {
  "chat": {
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "meta_tasks": {
    "title":    {"max_tokens": 80},
    "tags":     {"max_tokens": 60},
    "followups": {"max_tokens": 220}
  }
}
```

**qwen35-122b** (toggle + budget support):
```json
"param_translation": {
  "thinking": {
    "mode": "toggle",
    "on": {
      "enable_thinking": true,
      "chat_template_kwargs": {"enable_thinking": true}
    },
    "off": {
      "enable_thinking": false,
      "chat_template_kwargs": {"enable_thinking": false}
    },
    "budget_support": false
  }
},
"defaults": {
  "chat": {
    "temperature": 0.6,
    "top_p": 0.95,
    "max_tokens": 4096,
    "thinking": {"enabled": true}
  },
  "meta_tasks": {
    "title":    {"max_tokens": 80,  "thinking": {"enabled": false}},
    "tags":     {"max_tokens": 60,  "thinking": {"enabled": false}},
    "followups": {"max_tokens": 220, "thinking": {"enabled": false}}
  }
}
```

### Science model card (esmfold)

```json
{
  "id": "esmfold",
  "type": "structure",
  "description_short": "ESMfold protein structure prediction",
  "context_window": 0,
  "max_completion_tokens": 0,
  "endpoints": {
    "primary": "/v1/structure",
    "health": "/health"
  },
  "param_translation": {
    "thinking": {"mode": "none"},
    "max_tokens": {"field": null}
  },
  "defaults": {
    "inference": {
      "num_recycles": 3
    }
  },
  "custom_params": {
    "schema": {
      "num_recycles": {"type": "integer", "default": 3, "min": 1, "max": 20},
      "chunk_size": {"type": "integer", "default": 256}
    },
    "passthrough": true
  },
  "input_map": {
    "sequence": {
      "type": "string",
      "required": true,
      "pattern": "^[ACDEFGHIKLMNPQRSTVWY]+$",
      "max_length": 1022
    }
  },
  "output_map": {
    "pdb": {"type": "string"},
    "plddt": {"type": "array[float]"},
    "mean_plddt": {"type": "float"}
  },
  "deployment": {
    "gpu": true, "gpu_count": 1, "min_replicas": 0,
    "startup_seconds": 180, "custom_health": true
  }
}
```

## Gateway Behavior

### Request flow

```
1. Client sends request (OpenAI or Anthropic format)
2. Gateway resolves model → find card
3. Apply defaults from card for anything client didn't set
4. Detect meta-tasks (title/tags/followups via prompt sniffing)
   → Apply meta_task defaults from card (token caps, thinking overrides)
5. Translate params via card's param_translation
   → thinking: true → model-specific params
6. Validate custom params against card's custom_params.schema
7. Cap max_tokens to card's max_completion_tokens
8. Truncate input messages to card's context_window (if applicable)
9. Route to correct handler (chat/embedding/anthropic/rerank/forward)
10. Forward to model via knative-local-gateway
11. Return response (with protocol conversion if Anthropic endpoint)
```

### What the gateway does NOT do

- **No response stripping** — if the right params are sent, the model outputs clean responses
- **No per-model if/else** — all behavior is card-driven
- **No hardcoded model names** — models are discovered, not configured
- **No gateway redeploy for new models** — teams deploy ISVC + card, gateway auto-discovers

### Protocol conversion

The gateway accepts both OpenAI and Anthropic formats:

| Client sends | Gateway translates | Model receives |
|---|---|---|
| OpenAI `/v1/chat/completions` | Apply card defaults + param_translation | Model-specific format |
| Anthropic `/anthropic/v1/messages` | Convert Anthropic → OpenAI format, then apply card | Model-specific format |
| Direct `/v1/embeddings` | Reshape TEI input if needed | TEI-native or OpenAI format |
| Direct `/v1/rerank` | Reshape to TEI rerank format | TEI-native |
| Custom `/v1/structure` etc. | Forward as-is | Model's own server.py handles it |

### OpenAI ↔ Anthropic param mapping (gateway-level, not card-level)

This is protocol conversion, not model-specific. Always the same:

| OpenAI | Anthropic | Notes |
|---|---|---|
| `max_completion_tokens` | `max_tokens` | Required in Anthropic |
| `stop` | `stop_sequences` | |
| `system` role in messages | Top-level `system` param | |
| `reasoning_effort` | `thinking: {type, budget_tokens}` | Anthropic has exact budget |
| `tool_choice: "required"` | `tool_choice: {type: "any"}` | |
| `tool_choice: "none"` | `tool_choice: {type: "none"}` | |
| `tools[].function` | `tools[].input_schema` | |
| `top_p` | `top_p` | Same name |
| — | `top_k` | OpenAI doesn't have this |
| `n` | — | Anthropic doesn't support |

### Anthropic thinking → model translation

When a client sends Anthropic format with `thinking: {type: "enabled", budget_tokens: 8000}`:

1. Gateway converts Anthropic → OpenAI format (standard protocol conversion)
2. Gateway reads card's `param_translation.thinking`
3. If mode is "toggle": inject `enable_thinking: true` (budget is informational, model may not support it)
4. If mode is "effort": map budget to an effort level (heuristic: <2K → low, <8K → medium, else high)
5. If mode is "always_on": do nothing (model already thinks)
6. If mode is "none": ignore thinking param entirely

## Gateway Discovery — ConfigMaps + K8s Watches

**How models declare themselves:** Each model ships a `details.yaml` ConfigMap alongside its `inferenceservice.yaml`. The gateway reads these automatically. Teams deploy models the same way they do now — `kubectl apply` two files instead of one.

**Why ConfigMaps (not model-served `/details` endpoints):**
- Works for all model types — vLLM binaries, TEI binaries, llama.cpp, custom FastAPI. No need to modify any model server.
- Works when pods aren't running — models scaled to zero still have their card visible to the gateway.
- Teams already use `kubectl apply` for ISVCs. Adding a ConfigMap is the same workflow.
- Model servers still serve what they can at runtime (`/v1/models`, `/health`) — gateway queries these for live state when pods are running.

**Auto-updating via K8s Watches:**

Instead of polling every 60s, the gateway registers a Kubernetes Watch on both InferenceServices and ConfigMaps. K8s pushes a notification the instant anything changes:

```
Team does: kubectl apply -f esmfold-details.yaml
     ↓ (milliseconds)
K8s fires Watch event to gateway
     ↓
Gateway updates routing table immediately — no restart, no polling delay
```

Discovery flow:

```python
import kubernetes.client
from kubernetes.watch import Watch

def watch_models():
    """Watch for ISVC and ConfigMap changes. Instant updates."""
    v1 = kubernetes.client.CoreV1Api()
    custom = kubernetes.client.CustomObjectsApi()

    # Watch InferenceServices for pod lifecycle (ready, scaled to zero, etc.)
    for event in Watch().stream(custom.list_namespaced_custom_object,
            group="serving.kserve.io", version="v1beta1",
            namespace="models", plural="inferenceservices"):
        isvc = event["object"]
        handle_isvc_change(event["type"], isvc)

    # Watch ConfigMaps with model-details label for card changes
    for event in Watch().stream(v1.list_namespaced_config_map,
            namespace="models", label_selector="model-details=true"):
        cm = event["object"]
        handle_card_change(event["type"], cm)
```

On startup (before Watch connects), do a one-time list to seed the routing table. Watch takes over from there.

**What the gateway knows from each source:**

| Source | What it provides | When available |
|---|---|---|
| **ConfigMap card** | identity, type, context window, defaults, param_translation, compatibility, meta_tasks, endpoints, input/output maps, custom_params | Always — even when scaled to zero |
| **ISVC (K8s API)** | host, ready status, replica count, assigned node | Always — K8s state |
| **Model `/v1/models`** (vLLM) | actual `max_model_len`, served model name | Only when pod is running |
| **Model `/health`** (custom FastAPI) | loaded/not loaded, device, runtime state | Only when pod is running |
| **Model `/info`** (TEI) | pipeline type, max batch size | Only when pod is running |

The gateway merges all available sources. Card is the base. Runtime info supplements when the pod is up. If the pod is down, the card alone is enough for routing decisions.

**Adding a new model (what a team does):**

```bash
# 1. Create the InferenceService (same as today)
kubectl apply -f inferenceservice.yaml

# 2. Create the details card (one extra file)
kubectl apply -f details.yaml

# Gateway picks up both within milliseconds via Watch.
# No gateway restart. No gateway code changes.
```

**Card defaults — the model sets sensible defaults, user can override:**

The card's `defaults` section is the model team telling the gateway "if the user doesn't specify X, use this." For example, a small model defaults to short output, a big model defaults to long output:

```json
"defaults": {
  "chat": {
    "max_tokens": 4096,
    "temperature": 0.6,
    "top_p": 0.95,
    "streaming": true
  }
}
```

When a user sends `{"model": "qwen3-235b", "messages": [...]}` with nothing else, the gateway fills in the card defaults. If the user sends `{"max_tokens": 200}`, the user wins — card default is overridden.

This means the model team controls the experience. They know their model's sweet spots. The user can always override, but out of the box it works well.

## Comparison with POC

| Aspect | POC (172.26.92.232) | New cluster (172.26.92.230) |
|---|---|---|
| External domain | `inference.kubeflow.vulcan.alliancecan.ca` | `api.vulcan.alliancecan.ca` |
| Path prefix | `/serving/` | None — clean `/v1/` paths |
| Gateway config | 8+ hardcoded dicts (300+ lines) | Card-driven, zero hardcoded models |
| Thinking params | Per-model if/else in gateway | `param_translation` in card |
| Defaults | Hardcoded per model | `defaults` in card |
| Meta-tasks | Hardcoded caps + reasoning flag branches | `defaults.meta_tasks` in card |
| Custom params | Not supported | `custom_params.schema` + passthrough |
| Response stripping | Regex hacks (`_strip_thinking` etc) | Should not be needed — correct params = clean output |
| Anthropic endpoint | Partial (no thinking budget) | Full conversion with card-driven translation |
| GPU scheduling | GPU Operator | HAMi vGPU (`gpu=on` label, `nvidia.com/gpumem`) |
| Model discovery | k8s API polling (60s) + hardcoded EXTRA_MODELS | K8s Watches on ISVCs + ConfigMaps (instant) |
| Teams can add models | No — requires gateway code change | Yes — deploy ISVC + card |
| Tyk | Planned but never deployed | Deployed, pointing at model-gateway |

## Open Questions

1. **Streaming thinking tokens** — some models stream `<think/>` blocks, some don't include them in SSE. Card needs to declare this. Possible field: `param_translation.thinking.streams_thinking: true/false`

2. **Thinking token accounting** — thinking tokens count toward context on some models. Budget-aware truncation needs this. Card field: `param_translation.thinking.counts_toward_context: true/false`

3. **Tool calling format** — Qwen uses Hermes format, others use native OpenAI. Card field: `compatibility.tool_format: "openai" | "hermes" | null`

4. **Temperature recommendations vary by thinking mode** — Qwen recommends 0.6 for thinking, 0.7 for non-thinking. This could go in `defaults.chat.temperature` but may need mode-dependent defaults.

5. **How strict is custom_params validation?** — Reject invalid types/ranges? Or just warn and pass through?

6. **Card versioning** — what happens when a card schema changes? Need a `schema_version` field?

## Implementation Plan

### Phase 1: Gateway core — reliable, stable, scalable

**Goal**: Get the gateway running rock-solid before anything else. No models, no auth, just the routing infrastructure proven stable.

**1a. Gateway deployment**
- FastAPI app as Deployment + Service in `models` namespace
- Istio sidecar enabled (needs to reach knative-local-gateway)
- Health check: `/healthz` → returns 200 if discovery loop running
- Readiness check: `/readyz` → returns 200 if at least 1 model card loaded
- Graceful shutdown: drain in-flight requests, finish streaming responses
- Resource limits: 256Mi RAM, 500m CPU (it's a proxy, not compute)

**1b. Card-driven discovery**
- `discover()` queries InferenceServices + ConfigMaps on startup, refreshes every 60s
- Merges ISVC host/ready state with card metadata
- No hardcoded dicts. No model names in gateway code.

**1c. Per-type routing handlers**
- `chat` → forward to model, apply card defaults + param_translation
- `embedding` → reshape TEI ↔ OpenAI format
- `anthropic` → full Anthropic ↔ OpenAI protocol conversion
- `rerank` → Cohere/Jina format ↔ TEI format
- `forward` → pass through as-is (science models, custom endpoints)

**1d. Reliability features**
- **Request timeout**: configurable per-model via card (`deployment.timeout`), default 300s
- **Retry on scale-to-zero**: if model has `min_replicas: 0` and returns 503, gateway returns 503 with ETA from card's `deployment.startup_seconds`
- **Connection pooling**: reuse httpx clients per upstream host
- **Concurrency control**: per-model semaphore if card says `deployment.serialize: true`
- **Circuit breaker**: if a model fails N times in a row, temporarily stop routing to it
- **Streaming support**: SSE pass-through with proper backpressure
- **Structured logging**: JSON logs with model, user, tokens, latency, status for every request

**1e. Scaling**
- Gateway is stateless (all state from K8s API + cards). Can scale to multiple replicas.
- Knative handles model pod autoscaling (scale-to-zero, scale-up).
- Gateway itself runs as a regular Deployment (not Knative — always-on).
- Start with 1 replica. If CPU usage grows, scale to 2+.

**1f. Metrics endpoint**
- Expose `/metrics` in Prometheus format
- Counters: requests_total, tokens_prompt, tokens_completion, by model + user
- Histograms: request_duration_seconds by model
- Gauges: models_ready, models_total, discovery_last_success_timestamp
- Ready for ServiceMonitor scrape

### Phase 2: User authentication + key management

**Goal**: Every user who needs API access gets a Tyk API key tied to their username. Two provisioning paths: auto on Vulcan login, or manual by admin for remote/LDAP users.

**2a. Login-time key provisioning (Vulcan users)**
- `/etc/profile.d/` script on Vulcan login nodes (Warewulf overlay)
- Triggered on SSH login (not PAM — too early, NFS not mounted yet)
- Script checks `$HOME/.inference_api_key`:
  - Exists → load and export `INFERENCE_API_KEY`
  - Doesn't exist → generate key, register with Tyk, save to file
- Key file lives on NFS home (`global.storage.data.vulcan.local:/home`) → persists across sessions and login nodes
- Script:

```bash
# /etc/profile.d/inference-api-key.sh
KEYFILE="$HOME/.inference_api_key"
if [ ! -f "$KEYFILE" ]; then
    KEY=$(openssl rand -hex 32)
    USER=$(whoami)
    # Register with Tyk — username as alias, not LDAP bind
    curl -sf -X POST "https://api.vulcan.alliancecan.ca/tyk/keys" \
      -H "x-tyk-authorization: ${TYK_ADMIN_SECRET}" \
      -H "Content-Type: application/json" \
      -d "{\"alias\":\"${USER}\",\"access_rights\":{\"kserve-inference-proxy\":{\"versions\":{\"Default\":{}}}}}" \
      > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "$KEY" > "$KEYFILE"
        chmod 600 "$KEYFILE"
        echo "Inference API key created for ${USER}. Use \$INFERENCE_API_KEY."
    else
        echo "WARNING: Failed to create inference API key. Contact support." >&2
    fi
fi
export INFERENCE_API_KEY=$(cat "$KEYFILE" 2>/dev/null)
```

**2b. Key management API**
Tyk OSS provides REST API for key lifecycle:

| Action | Tyk API | Who uses it |
|---|---|---|
| Create key | `POST /tyk/keys` | Login script, admin CLI |
| List keys | `GET /tyk/keys` | Admin |
| Get key details | `GET /tyk/keys/{key}` | Admin, user CLI |
| Regenerate key | `POST /tyk/keys/{key}/regenerate` | User CLI, admin |
| Revoke key | `DELETE /tyk/keys/{key}` | User CLI, admin |
| Find by alias | `GET /tyk/keys?p={alias}` | Admin lookup by username |

**2c. User-facing CLI** (`inference-key`)
A single bash script deployed via Warewulf to all login nodes. Uses the Tyk REST API.

```bash
# Self-service (any user, operates on own key):
inference-key info           # show my key, alias, rate limits, last used
inference-key regenerate     # revoke old key, create new one, update $HOME/.inference_api_key
inference-key revoke         # revoke my key (e.g. compromised)
inference-key test           # test my key against the API (hit /v1/models)

# Admin commands (cluster admins only):
inference-key create <username>              # manually create a key for a user
inference-key create <username> --rate 100   # create with custom rate limit (req/min)
inference-key list                           # list all keys with aliases
inference-key show <username>                # show details for a specific user
inference-key revoke <username>              # admin revoke for a specific user
inference-key regenerate <username>          # admin regenerate for a specific user
inference-key set-rate <username> <rate>     # change rate limit
```

The script is self-contained — calls Tyk REST API via `curl`, reads admin secret from `/etc/inference/tyk-admin-secret`.

**Manual key creation** (most important use case):
```bash
# Admin creates a key for a new user or someone who lost theirs
$ inference-key create jsmith
Key created for jsmith: a1b2c3d4e5f6...
Saved to /home/jsmith/.inference_api_key

# User can now use it:
$ echo $INFERENCE_API_KEY
a1b2c3d4e5f6...

# Or if they're not logged in yet, they'll pick it up on next login
```

**Key regeneration:**
```bash
$ inference-key regenerate
Old key revoked. New key: f6e5d4c3b2a1...
Updated /home/rahimk/.inference_api_key
Run: export INFERENCE_API_KEY=$(cat ~/.inference_api_key)
```

**2d. Remote / non-Vulcan users**

Not all users SSH into Vulcan. Researchers on other Alliance clusters (Cedar, Narval, Graham) or collaborators outside Alliance may need API access. They're in LDAP but never touch Vulcan login nodes.

Two paths for non-Vulcan users:

**Admin creates key manually:**
```bash
# On Vulcan login node (admin):
inference-key create jsmith                   # creates key, saves to /home/jsmith/.inference_api_key

# For users WITHOUT a Vulcan $HOME (no NFS home here):
inference-key create jsmith --output-only     # creates key, prints to stdout, no file write
# → Key: a1b2c3d4e5f6...
# Admin sends this to the user out-of-band (email, Slack, etc.)
```

**Self-service key creation via API endpoint:**
The gateway exposes a public key-registration endpoint for users who have LDAP credentials but no Vulcan access:

```
POST https://api.vulcan.alliancecan.ca/auth/register
{
  "username": "jsmith",
  "password": "<ldap-password>"
}
```

Flow:
1. Gateway receives username + password
2. Validates against LDAP (simple bind to Alliance LDAP server)
3. If bind succeeds: create Tyk key with `alias: "jsmith"`, return the key
4. If bind fails: return 401

This is optional — can start with admin-only key creation and add self-service later. But the LDAP bind approach means:
- No need for users to SSH into Vulcan
- No need for admins to manually create keys for every external user
- Key is tied to a real LDAP identity (validated at creation time)
- Subsequent requests use the Tyk key, not LDAP (fast, no LDAP bind per request)

**Key management for remote users:**
Remote users can't use the `inference-key` CLI (not on Vulcan). They use the API directly:
```bash
# Get my key info
curl https://api.vulcan.alliancecan.ca/auth/info \
  -H "Authorization: Bearer $INFERENCE_API_KEY"

# Regenerate my key (requires LDAP re-auth to prevent stolen-key regeneration)
curl -X POST https://api.vulcan.alliancecan.ca/auth/regenerate \
  -d '{"username":"jsmith","password":"<ldap-password>"}'
```

**2e. Username as identity, not LDAP bind**
- Tyk key has `alias: "<username>"` — the LDAP username
- For Vulcan users: from `$(whoami)` at login time
- For remote users: from LDAP bind at registration time
- No ongoing LDAP integration in Tyk. LDAP is used ONCE at key creation to prove identity.
- Analytics and usage tracking use the alias → maps to LDAP user for reporting
- Simple, stateless, no LDAP connector to maintain for request routing

**2f. Key security**
- Keys are 64-char hex (256-bit), stored in `$HOME/.inference_api_key` (NFS, mode 600)
- Remote users store keys however they want (env var, config file, secrets manager)
- Tyk validates keys on every request — invalid key = 403
- Rate limits per key (configurable per user group if needed)
- Admin secret for Tyk API stored in K8s Secret, not in the profile script
  - Login script reads it from a config file mounted via Warewulf: `/etc/inference/tyk-admin-secret`
- Key regeneration for remote users requires LDAP re-auth (prevents stolen-key abuse)

### Phase 3: Compute usage logging

**Goal**: Track per-user resource usage for Alliance reporting. Full accounting of what hardware was consumed, by whom, for how long.

**Monitoring philosophy**: This cluster's job is scaling nodes (Warewulf) and scaling models (K8s). Monitoring infrastructure is NOT this cluster's job. Zero extra monitoring pods.

**3a. Gateway structured JSON logs (stdout)**
Every request logged as one JSON line to stdout. K8s captures these. Simple, zero overhead:

```json
{
  "ts": "2026-06-04T10:23:45.123Z",
  "request_id": "req-a1b2c3d4",

  "user": "rahimk",
  "model": "qwen3-235b",
  "endpoint": "/v1/chat/completions",
  "status": 200,
  "streaming": true,
  "thinking_enabled": true,

  "tokens_prompt": 847,
  "tokens_completion": 412,
  "tokens_total": 1259,
  "tokens_thinking": 3200,
  "tokens_estimated": false,

  "gpu": true,
  "gpu_type": "L40S",
  "gpu_scheduler": "hami",
  "hami_vgpu_count": 4,
  "hami_vram_mb": 46068,
  "hami_cores_pct": 100,

  "physical_gpu_count": 4,
  "physical_gpu_vram_mb_each": 46068,

  "system_ram_mb": 527849,
  "cpu_count": 64,
  "node": "rack15-03",

  "duration_ms": 2340,
  "duration_queue_ms": 45,
  "duration_inference_ms": 2295,

  "model_framework": "vllm",
  "model_precision": "awq-int4"
}
```

Where each field comes from:

| Field | Source | Notes |
|---|---|---|
| `user` | Tyk key alias | Set during key creation |
| `model` | Request body | Model ID from client |
| `tokens_*` | Response `usage` field | Fallback: estimate, set `tokens_estimated: true` |
| `gpu` | Details card `deployment.gpu` | Whether model uses GPU at all |
| `gpu_type` | Details card `deployment.gpu_type` | e.g. "L40S", "A100" |
| `gpu_scheduler` | "hami" | Always "hami" on this cluster |
| `hami_vgpu_count` | Pod resource request `nvidia.com/gpu` | Number of vGPU slices allocated |
| `hami_vram_mb` | Pod resource request `nvidia.com/gpumem` | VRAM requested in MiB |
| `hami_cores_pct` | Pod resource request `nvidia.com/gpucores` | Compute core percentage (0-100 per slice) |
| `physical_gpu_count` | Details card `deployment.gpu_count` | How many physical GPUs the model spans |
| `physical_gpu_vram_mb_each` | `nvidia-smi` on node (46268 for L40S) | Per-card VRAM |
| `system_ram_mb` | Node `status.capacity.memory` | From K8s node info |
| `cpu_count` | Node `status.capacity.cpu` | From K8s node info |
| `node` | Pod's assigned node | Which worker served it |
| `duration_ms` | Gateway timer | Total wall clock |
| `duration_queue_ms` | Gateway timer | Time in queue (serialized models) |
| `duration_inference_ms` | Response time - request time | Actual model compute |
| `model_framework` | Details card `framework` | vllm, tei, custom, etc. |
| `model_precision` | Details card `precision` | fp16, awq-int4, etc. |

**How HAMi GPU slicing works on this cluster:**

HAMi splits each physical GPU into `deviceSplitCount` (10) virtual slices. Each slice gets a share of VRAM and compute cores. A pod requests resources like:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1           # 1 vGPU slice
    nvidia.com/gpumem: 4606     # ~1/10 of L40S 46068 MiB
    nvidia.com/gpucores: 30     # 30% of compute cores
```

For multi-GPU models (e.g. qwen3-235b on 4 GPUs):
```yaml
resources:
  limits:
    nvidia.com/gpu: 4           # 4 full GPUs (each counts as 10 vGPU slices internally)
    nvidia.com/gpumem: 46068    # full VRAM per GPU
```

Current allocatable: `nvidia.com/gpu: 40` (4 physical × 10 slices on rack15-03)

**GPU-hours calculation** (done in reporting, not in logs):
```
# Fraction of a single physical GPU consumed:
gpu_fraction = hami_vram_mb / physical_gpu_vram_mb_each

# Total physical GPU-equivalent hours:
gpu_hours = (duration_ms / 3600000) × physical_gpu_count × gpu_fraction
```

Examples:
- bge-small (CPU): 0 gpu_hours
- command-r-7b (1 vGPU slice, 4606 MiB, 10 min): 0.017 gpu_hours
- qwen3-235b (4 full GPUs, 10 min): 0.67 gpu_hours
- esmfold (1 full GPU, 5 min): 0.083 gpu_hours

**3b. Tyk analytics → Redis (already running)**
Tyk OSS writes request analytics to Redis by default:
- API key (→ username via alias)
- Request path, method, status code
- Latency, response size, timestamp

Query with: `redis-cli -h tyk-redis-master.tyk.svc.cluster.local`

**3c. Usage reporting script**
A simple script (cron or on-demand) that:
1. Pulls from Tyk Redis analytics + gateway pod logs
2. Aggregates per-user, per-model, per-day
3. Outputs CSV for Alliance reporting

```bash
# Daily usage report
inference-usage-report --day 2026-06-04
```

Output CSV fields:
```
date, user, model, requests, tokens_prompt, tokens_completion, tokens_thinking,
gpu_type, gpu_scheduler, hami_vgpu_count, hami_vram_mb, hami_cores_pct,
physical_gpu_count, physical_gpu_vram_mb_each,
system_ram_mb, cpu_count, node,
duration_total_ms, duration_queue_ms, duration_inference_ms, gpu_hours,
model_framework, model_precision
```

This runs on a login node or cron, not on the cluster.

**3d. Gateway `/metrics` endpoint (future-proofing)**
Expose Prometheus-format metrics at `/metrics` — but DON'T deploy Prometheus on this cluster.
When someone decides where Prometheus lives (dedicated instance, Alliance monitoring),
the endpoint is ready to scrape:
- `inference_tokens_prompt_total{model, user, gpu_type}`
- `inference_tokens_completion_total{model, user}`
- `inference_requests_total{model, user, status, gpu_type}`
- `inference_request_duration_seconds{model, gpu_type}` (histogram)
- `inference_gpu_hours_total{model, user, gpu_type}`

**3e. Token counting**
- vLLM models: token counts from response `usage` field (accurate)
- TEI models: token counts from TEI response (accurate)
- Custom FastAPI models: from model's `server.py` response (accurate if provided)
- Gateway fallback: estimate from input/output length (rough, logged as `"tokens_estimated": true`)

**3f. Thinking token accounting**
For reasoning models, thinking tokens are tracked separately:
- `tokens_thinking`: tokens spent on reasoning (from model response or estimated)
- These count toward total usage but are logged separately
- Some models can't separate thinking from output (phi-4 always-on) — logged as `tokens_thinking: -1` with note

### Phase 4: Deploy + wire up external access

- Rewire Tyk to point at `model-gateway.models.svc.cluster.local:80`
- Configure Traefik IngressRoute for `api.vulcan.alliancecan.ca` → Tyk
- TLS certificate for `api.vulcan.alliancecan.ca` (cert-manager + DNS-01 challenge, or manual)
- DNS entry pointing to cluster's external IP
- Test: `curl https://api.vulcan.alliancecan.ca/v1/models -H "Authorization: Bearer $KEY"`

### Phase 5: Port models from POC (172.26.92.232 → 172.26.92.230)

**Important**: The POC cluster (172.26.92.232) will be **destroyed** and its nodes added to this cluster via Warewulf. So this is a migration, not a parallel deployment.

Differences between clusters:

| Aspect | POC (232) | New cluster (230) |
|---|---|---|
| GPU scheduling | NVIDIA GPU Operator | HAMi vGPU |
| GPU type selector | `nvidia.com/gpu.product: NVIDIA-L40S` | `gpu: "on"` label |
| GPU request | `nvidia.com/gpu: 4` | `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 46068` |
| GPU time-slicing | NVIDIA operator config | HAMi `deviceSplitCount: 10` |
| Model manifests | Need nodeSelector changes | Need HAMi resource format |

Porting checklist per model:
1. Write details card (or use existing one from POC)
2. Update InferenceService: replace GPU operator selectors with HAMi format
3. Deploy ISVC + card → gateway auto-discovers
4. Verify routing + response
5. Repeat

Order: CPU models first → single-GPU models → multi-GPU models → science models

## Cluster Migration Plan (232 → 230)

The POC cluster nodes will be reprovisioned via Warewulf and added as workers to this cluster. This is the long-term scaling path.

**Current state:**
- 172.26.92.230: control plane + 1 GPU worker (rack15-03, 4× L40S)
- 172.26.92.232: separate POC cluster with 4 GPU workers (16× L40S total)

**Target state:**
- 172.26.92.230: control plane + 5 GPU workers (20× L40S total)
- 172.26.92.232: decommissioned as separate cluster, nodes join 230's cluster

**Steps:**
1. Ensure all models are portable (have details cards, HAMi-compatible manifests)
2. Verify gateway is stable on 230
3. Drain and reprovision POC workers via Warewulf
4. Join them to 230's RKE2 cluster as additional workers
5. HAMi automatically detects new GPUs, allocatable vGPU count increases
6. Models spread across more nodes via Knative autoscaling
- Each model: write card + deploy ISVC → gateway auto-discovers, zero gateway changes

## Cluster Roles

| Component | Job | Not its job |
|---|---|---|
| **172.26.92.230** (this cluster) | Scale nodes via Warewulf, scale models via K8s, route inference requests | Prometheus, Grafana, monitoring stack |
| **POC nodes** (currently 232) | Will be reprovisioned via Warewulf and joined to 230 as additional GPU workers | Running as separate cluster |
| **Vulcan login nodes** | User access, key provisioning (`inference-key`), usage reporting scripts | — |
| **Monitoring** (TBD) | Prometheus + Grafana somewhere — not on this cluster | — |

## Implementation Priority

```
Phase 1: Gateway core (reliable, stable, scalable)     ← START HERE
Phase 2: User auth + key management
Phase 3: Usage logging (JSON logs + Redis, no monitoring stack)
Phase 4: External access (domain + TLS)
Phase 5: Port models from POC
```

Phases 1–3 can be tested entirely inside the cluster with `curl` pods.
Phase 4 opens it to users.
Phase 5 adds models incrementally after the platform is proven.
