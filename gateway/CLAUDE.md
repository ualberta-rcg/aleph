# Gateway Notes

This guide covers operating and extending the FastAPI inference gateway in `gateway/`.

## Scope

Gateway responsibilities:
- Model catalog and capability routing
- OpenAI-compatible `/v1/chat/completions`, `/v1/embeddings`, `/v1/rerank`
- Anthropic-compatible `/v1/messages` translation
- Thinking/reasoning parameter translation + stripping behavior
- Tool support gating by model card metadata

## Key files

- `app/gateway.py` — primary request handling and forwarding
- `app/anthropic_xlate.py` — Anthropic <-> OpenAI translation layer
- `cards/*.yaml` — gateway-facing model card metadata
- `k8s/deployment.yaml` — gateway Deployment (image tag pin)
- `tyk/*.json` + `tyk/tyk-keys.sh` — Tyk API definitions and key helpers

## Versioning and rollout

### CI publish (Docker Hub)

`.github/workflows/deploy-gateway.yml` builds `gateway/Dockerfile` and pushes to
Docker Hub on `main` pushes that touch `gateway/**`.

- Default image: `rkhoja/aleph`
- Tags: immutable `gateway-<shortsha>` + moving `latest`
- Secrets (same names as `warewulf-rke2-hami`): `DOCKER_HUB_USER`, `DOCKER_HUB_TOKEN`
- Optional: `DOCKER_HUB_REPO` secret or repo Variable to override the image name

Manual run: Actions → **Build & Push Gateway Image** → **Run workflow**.

### Cluster rollout (local build, no registry)

1. Update code in `app/`.
2. Build image on control-plane host via deploy flow.
3. Bump image tag in `k8s/deployment.yaml`.
4. Roll out and wait for deployment readiness.
5. Re-run compatibility tests (`scratch/full_test.py`).

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
