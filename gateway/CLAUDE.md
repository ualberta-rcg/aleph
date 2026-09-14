# Gateway Notes

This guide covers operating and extending the FastAPI inference gateway in `gateway/`.

## Scope

Gateway responsibilities:
- Model catalog and capability routing (no hardcoded model names)
- OpenAI-compatible `/v1/chat/completions`, `/v1/embeddings`, `/v1/rerank`
- Anthropic-compatible `/v1/messages` translation (chat-type LLMs only)
- Science/custom model catch-all forward via `/v1/{path:path}`
- Thinking/reasoning parameter translation + stripping behavior
- Tool support gating by model card metadata
- Scale-to-zero detection + cold-start wake-up guard (two cold 503s: wake with
  estimate-derived Retry-After, or capacity refusal with no wake)
- Per-request usage accounting to a persistent JSONL ledger + Prometheus `/metrics`
  (cluster-wide fan-in)

Full architecture and API docs: see `gateway/README.md`

## Key files

- `app/gateway.py` — primary request handling, forwarding, and Anthropic<->OpenAI translation
- `app/conversation.py` — OpenAI⇄Anthropic conversation translation helpers
- `app/capacity.py` — cold-start GPU-fit simulation (HAMi metrics parsing)
- `app/usage.py` — usage records + JSONL ledger
- `cards/*.yaml` — gateway-facing model card metadata (almost all live in per-model dirs)
- `k8s/{deployment,rbac,service}.yaml` — Deployment (control-plane, no GPUs), RBAC, Service
- `tyk/*.json`, `tyk/middleware/*.js`, `tyk/tyk-keys.sh` — Tyk API definitions, JSVM middleware, key helper
- `test.py` (+ `tests/`) — model-agnostic gateway battery and CI regressions
- `README.md` — full architecture, API mapping, deploy instructions

## Gateway fields from details.yaml

The gateway reads these fields from model cards ("Required" below = needed for the
behavior to work, not parser validation — the parser only requires a nonempty `id`;
see [models/details.md](../models/details.md) for the authoritative reference):

| Field | Used for | Required |
|---|---|---|
| `routing.k8s_name` | ISVC name lookup (defaults to model ID) | No |
| `routing.upstream_model_id` | Rewrite model name for backend | No |
| `routing.no_stream` | Disable streaming | No |
| `behavior.supports_tools` | Tool calling gate (400 if unsupported) | Yes for LLMs |
| `behavior.strips_thinking` | Strip reasoning from responses | Yes for reasoning models |
| `behavior.reasoning_model` | Reasoning-specific logic | Yes for reasoning models |
| `behavior.supports_vision` | Catalog advertising | Yes for vision models |
| `param_translation.thinking.*` | Effort → budget mapping | Yes for reasoning models |
| `defaults.chat.*` | Auto-fill missing params | Recommended for LLMs |
| `defaults.meta_tasks.*` | OpenWebUI title/tags/followups | Recommended for LLMs |
| `limits.context_window` | Catalog/docs + usage-record metadata (no gateway-side input enforcement) | Recommended |
| `limits.max_completion_tokens` | Caps prepared chat output tokens | Yes for chat |
| `scaling.scale_to_zero` | Catalog/listing metadata (cold guard reads observed state) | Yes |
| `scaling.cold_start_estimate` | ETA + Retry-After in the cold 503 | Recommended |

**Note:** The gateway reads `behavior.*` (not `compatibility.*`). Some older cards use `compatibility.supports_tools` — that field is NOT read by the gateway. Use `behavior` for gateway-facing feature flags.

## Anthropic endpoint gating

`/v1/messages` (and `/anthropic/v1/messages` after Tyk strips the prefix) only works
for `type: "chat"` models. Non-chat models are rejected with 400 `anthropic_unsupported`.
`GET /v1/models` on the Anthropic surface (`X-Aleph-Api: anthropic` or `anthropic-version`)
returns always-on chat models only, in Anthropic list shape — any chat model remains
callable. `POST /v1/messages/count_tokens` is a dedicated handler (not the catch-all).

## Versioning and rollout

### CI publish + cluster rollout (Docker Hub — default)

`.github/workflows/deploy-gateway.yml` builds `gateway/Dockerfile` and pushes to
Docker Hub on `main` pushes that touch `gateway/**`.

- Image: `rkhoja/aleph` (`latest` + immutable `gateway-<shortsha>`)
- Live Deployment (`63-model-gateway.yaml`): pinned `gateway-<sha>`, `imagePullPolicy: IfNotPresent`
- Rollout: bump the pin, then `kubectl set image deploy/model-gateway -n models gateway=rkhoja/aleph:gateway-<sha>`
- A Warewulf rebuild resurrects whatever tag is in the overlay — never leave live on `:latest`.

### Local build (dev / air-gapped fallback only)

See the ops runbook (maintained in the operators' local working dir) for the local-build /
air-gapped fallback. Do not use for day-to-day deploys.

## Behavior guardrails

- Keep endpoint compatibility stable unless intentionally versioned.
- Do not leak reasoning content for models/cards marked to strip thinking.
- Validate tool usage against `supports_tools`; return clear 400 on unsupported models.
- Preserve pass-through behavior for supported request params when possible.

## Parameter compatibility notes

- OpenAI `reasoning_effort` values may be broader than backend-native levels.
- Anthropic thinking may arrive as adaptive effort or legacy budget tokens.
- Normalize to backend-supported levels rather than hard-fail when safe.
- Prefer transparent mapping rules documented in code comments.

## Secrets and config

- No secret values in code or committed manifests.
- Tyk admin secret comes from environment (`TYK_SECRET` / `TYK_API_SECRET`).
- Load env from repo root `.env` when running admin scripts.

## Testing expectations after gateway changes

Run the model-agnostic battery (and the CI regressions in `tests/`):

```bash
GW_URL=https://<hostname> TYK_KEY=<key> python3 gateway/test.py   # FLEET=1 warms + probes every model
```

Check: chat non-stream + stream, Anthropic translation path, reasoning level
handling + strip behavior, tool call pass/block, embeddings + rerank unaffected.

## Optional model-specific notes

If a gateway behavior is model-specific (parser quirks, tool-choice caveats, special params),
record it in that model directory as `models/<model>/CLAUDE.md` and keep the card in sync.
