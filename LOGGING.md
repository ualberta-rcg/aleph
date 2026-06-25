# Usage Accounting & Logging

The gateway emits a structured **usage record** for every request so we can do
SLURM-style fairshare/accounting: who used which model, how many tokens, on what
hardware, for how long, and whether the call paid a cold-start cost.

See also: [TYK-USERS.md](TYK-USERS.md) (identity/keys), `gateway/README.md`.

## Where it goes

- File: `GATEWAY_USAGE_LOG` (default **`/var/log/aleph/usage.log`**), one JSON
  object per line (JSON-lines), rotated (50 MB × 5 by default).
- Storage: an **`emptyDir`** mounted into the gateway pod. It is intentionally
  **in-pod**, kept separate from application stdout, and **never written to the
  host**. Ship it to a central system out of band later (promtail / fluent-bit /
  Vector → Loki/Elasticsearch/Prometheus).
- If the file handler can't be created the logger falls back to stdout so events
  are never silently dropped.

```bash
# Tail it live:
kubectl exec -n models deploy/model-gateway -c gateway -- tail -f /var/log/aleph/usage.log

# Copy a snapshot out:
kubectl exec -n models deploy/model-gateway -c gateway -- cat /var/log/aleph/usage.log > usage.log
```

Config (env on the gateway Deployment, `63-model-gateway.yaml`):

| Env | Default | Meaning |
|---|---|---|
| `SITE_NAME` | `aleph` | stamped on every record as `site` (set per cluster) |
| `GATEWAY_USAGE_LOG` | `/var/log/aleph/usage.log` | log path (inside the emptyDir) |
| `GATEWAY_USAGE_LOG_MAX_BYTES` | `52428800` | rotation size |
| `GATEWAY_USAGE_LOG_BACKUPS` | `5` | rotated copies kept |

## Record schema

```json
{
  "ts": "2026-06-25T02:25:04Z",
  "site": "aleph",
  "identity": "openwebui",
  "identity_type": "service",
  "account": "shared-pool",
  "endpoint": "/v1/chat/completions",
  "api": "openai",
  "model": "gemma-3-4b-it",
  "status": 200,
  "stream": false,
  "cold_start": false,
  "latency_ms": 765,
  "tokens": {
    "prompt": 15,
    "completion": 6,
    "total": 21,
    "detail": {
      "prompt_tokens": 15,
      "completion_tokens": 6,
      "total_tokens": 21,
      "prompt_tokens_details": null,
      "completion_tokens_details": { "reasoning_tokens": 0 }
    }
  },
  "context_window": 131072,
  "max_completion_tokens": 8192,
  "resources": {
    "model": "gemma-3-4b-it",
    "gpus": 1,
    "vram_mib": 20480,
    "cpu_cores": 8.0,
    "system_ram_mib": 24576,
    "node": "rack15-03",
    "gpu_product": "L40S",
    "latency_ms": 765
  },
  "derived": { "gpu_seconds": 0.765 }
}
```

### Fields

| Field | Meaning |
|---|---|
| `ts` | UTC timestamp (ISO-8601, `Z`) |
| `site` | cluster tag (`SITE_NAME`) — lets multiple sites pool into one ledger |
| `identity` / `account` / `identity_type` | caller identity from Tyk (`anonymous` if not via Tyk) — see [TYK-USERS.md](TYK-USERS.md) |
| `endpoint` / `api` | `/v1/chat/completions`,`/v1/messages`,`/v1/embeddings`,`/v1/rerank`,`/v1/<custom>`; api = `openai`/`anthropic`/`cohere`/`custom` |
| `model` | model id |
| `status` | upstream HTTP status (200 served, 503 cold-start, 4xx errors) |
| `stream` | whether the client streamed (SSE) |
| `cold_start` | `true` for a scale-from-zero 503 event (a wake-up was fired) |
| `latency_ms` | gateway↔upstream round trip (0 for cold-start events) |
| `tokens.prompt/completion/total` | normalized counts for easy aggregation |
| `tokens.detail` | the **verbatim** upstream `usage` object — preserves engine-specific breakdowns (`completion_tokens_details.reasoning_tokens`, `prompt_tokens_details.cached_tokens`, audio, …) whenever vLLM emits them |
| `context_window` / `max_completion_tokens` | the model card's declared limits |
| `resources` | allocated compute footprint + hardware (below) |
| `derived.gpu_seconds` | `gpus × latency_ms/1000` — a simple GPU-time unit for fairshare |

### Where the compute facts come from

- `gpus`, `vram_mib`, `cpu_cores`, `system_ram_mib` — the model's **ISVC predictor
  resource spec** (HAMi vGPU requests). With HAMi a model may hold a *slice* of a
  card, so `vram_mib` can be < the physical 48 GB.
- `node`, `gpu_product` — resolved live: `model → predictor pod → node`, then the
  node's `aleph.gpu/product` label. Those labels are written by the **node-labeler
  DaemonSet** (`11-node-labeler.yaml`), which auto-detects GPU/CPU/RAM per worker.

> Note: `resources` is the **allocated** footprint, not live utilization. Live
> GPU%/instantaneous VRAM needs a metrics exporter (DCGM / HAMi exporter) and is
> not wired here.

## Token detail — what to expect

Plain chat/instruct models report just prompt/completion/total (the detail keys are
present, often `null`). **Reasoning** models additionally populate
`completion_tokens_details.reasoning_tokens`, and prompt caching populates
`prompt_tokens_details.cached_tokens`. Because we log the upstream `usage` verbatim
in `tokens.detail`, those appear automatically without any gateway change — you can
separate "thinking" tokens from answer tokens downstream.

For **streamed** chat the gateway sets `stream_options.include_usage` so the final
SSE chunk carries `usage`; that is captured into the record (`stream: true`). If an
upstream/streamed call ends without a usage chunk, token counts may be 0 for that
record (best-effort) while identity/resources/latency are still logged.

## Cold starts in the ledger

A scale-from-zero wake-up is logged as its own record with `cold_start: true`,
`status: 503`, and zero tokens — because spinning a model up burns GPU time before
any token is produced. A client retrying a cold model therefore produces several
`cold_start: true` records followed by one served `200`. Example (a real wake-up of
`gemma-3-4b-it` from a login node): 15 × `cold_start:true` 503, then 1 × `200`.

## Prometheus metrics

`GET /metrics` exposes per-model rollups derived from the same events:

```
gateway_model_requests_total{model="..."}
gateway_model_prompt_tokens_total{model="..."}
gateway_model_completion_tokens_total{model="..."}
gateway_model_cold_starts_total{model="..."}
gateway_model_gpu_seconds_total{model="..."}
```

plus the global gauges (`gateway_requests_total`, `gateway_models_ready`, …). These
are in-process counters (reset on pod restart); the JSON-lines file is the durable
source of truth.

## Example: aggregating the ledger

```bash
# GPU-seconds per account, this file:
kubectl exec -n models deploy/model-gateway -c gateway -- cat /var/log/aleph/usage.log \
 | python3 -c '
import sys, json, collections
acct = collections.defaultdict(float); tok = collections.defaultdict(int)
for line in sys.stdin:
    d = json.loads(line)
    acct[d["account"]] += d["derived"]["gpu_seconds"]
    tok[d["account"]]  += d["tokens"]["total"]
for a in sorted(acct, key=acct.get, reverse=True):
    print(f"{a:20s} gpu_s={acct[a]:8.1f}  tokens={tok[a]}")
'
```

## Node hardware labels (`11-node-labeler.yaml`)

The labeler stamps each GPU worker so the gateway (and any scheduler/report) can
read hardware facts off the Node object:

| Label | Example |
|---|---|
| `aleph.gpu/product` | `L40S` |
| `aleph.gpu/count` | `4` |
| `aleph.gpu/memory-mib` | `46068` |
| `aleph.cpu/model` | `Intel_R__Xeon_R__Gold_6448Y` (sanitized to label rules) |
| `aleph.cpu/cores` | `64` |
| `aleph.node/memory-gib` | `503` |

```bash
kubectl get nodes -L aleph.gpu/product,aleph.gpu/count,aleph.cpu/cores,aleph.node/memory-gib
```
