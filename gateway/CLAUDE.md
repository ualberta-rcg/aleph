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
- Scale-to-zero detection + cold-start wake-up guard

Full architecture and API docs: see `gateway/README.md`

## Key files

- `app/gateway.py` — primary request handling, forwarding, and Anthropic<->OpenAI translation (single-file)
- `cards/*.yaml` — gateway-facing model card metadata (most live in per-model dirs)
- `k8s/deployment.yaml` — gateway Deployment (runs on control-plane, no GPUs)
- `tyk/*.json` + `tyk/tyk-keys.sh` — Tyk API definitions and key helpers
- `README.md` — full architecture, API mapping, deploy instructions

## Gateway fields from details.yaml

The gateway reads these fields from model cards. When creating/updating `details.yaml`, make sure these are present:

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
| `limits.context_window` | Hard context cap | Yes |
| `limits.max_completion_tokens` | Hard output cap | Yes |
| `scaling.scale_to_zero` | Cold-start guard | Yes |
| `scaling.cold_start_estimate` | ETA in 503 message | Recommended |

**Note:** The gateway reads `behavior.*` (not `compatibility.*`). Some older cards use `compatibility.supports_tools` — that field is NOT read by the gateway. Use `behavior` for gateway-facing feature flags.

## Anthropic endpoint gating

`/v1/messages` only works for `type: "chat"` models. Non-chat models (embed, predict, forecast, etc.) are rejected with 400 `anthropic_unsupported`. This prevents confusing errors from upstream vLLM when Anthropic-formatted requests hit non-LLM backends.

## Versioning and rollout

### CI publish + cluster rollout (Docker Hub — default)

`.github/workflows/deploy-gateway.yml` builds `gateway/Dockerfile` and pushes to
Docker Hub on `main` pushes that touch `gateway/**`.

- Image: `rkhoja/aleph` (`latest` + immutable `gateway-<shortsha>`)
- Deployment: `k8s/deployment.yaml` uses `imagePullPolicy: IfNotPresent`
- Rollout: `./deploy-aleph/deploy.sh` or `kubectl set image deploy/model-gateway -n models gateway=rkhoja/aleph:<tag>`
- Pin CI tags for reproducibility; use `latest` for the newest build.

### Local build (dev / air-gapped fallback only)

See docs/RUNBOOK.md appendix (local-build / air-gapped fallback). Do not use for day-to-day deploys.

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

- Chat completion non-stream + stream
- Anthropic translation path
- Reasoning level handling + strip behavior
- Tool call pass/block behavior
- Embeddings + rerank endpoints unaffected by chat changes

## Optional model-specific notes

If a gateway behavior is model-specific (parser quirks, tool-choice caveats, special params),
record it in that model directory as `models/<model>/CLAUDE.md` and keep the card in sync.
