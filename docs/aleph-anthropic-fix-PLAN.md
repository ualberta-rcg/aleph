# Aleph gateway: restore /anthropic endpoint + gateway improvements

> Status: implemented 2026-08-25 (plus audio usage counts in `tokens.detail`).
> Live pin and canary notes are in `CHANGELOG.md`.

Handoff plan, written 2026-08-25. Execute from a workstation with push access to
[ualberta-rcg/aleph](https://github.com/ualberta-rcg/aleph) and SSH to aleph1.
All findings below were verified live on 2026-08-25.

## Context you need

- Cluster: **aleph** — stateless Warewulf-provisioned RKE2. Head node aleph1 = `172.26.92.43`
  (`ssh 172.26.92.43`; kubectl: `export PATH=$PATH:/var/lib/rancher/rke2/bin KUBECONFIG=/etc/rancher/rke2/rke2.yaml`).
  Anything not committed to the repo's `ww-overlays/` is WIPED on every cluster rebuild.
- Public edge: `https://inference.vulcan.alliancecan.ca` → MetalLB VIP on 172.26.92.43 →
  **Tyk** (auth, rate limits, namespace `tyk`) → `model-gateway.models.svc:80`
  (FastAPI, 3 replicas, source `gateway/app/gateway.py`) → KServe/Knative model pods.
- Gateway images are built ONLY by repo CI: `.github/workflows/deploy-gateway.yml` builds
  `gateway/Dockerfile` and pushes `rkhoja/aleph:gateway-<shortsha>` to Docker Hub on every
  push to `main` touching `gateway/**` (~4 min). Never build/import images by hand.
- Deployment manifest (also the rebuild source of truth):
  `ww-overlays/overlays/control-plane/etc/rancher/manifests/63-model-gateway.yaml`,
  currently pinned to `rkhoja/aleph:gateway-b37897c`.
- LIVE FACT: image `gateway-b37897c` is byte-identical to repo HEAD for `gateway/app/`
  (`git diff b37897c..HEAD -- gateway/app/` is empty). The gateway code is NOT the bug.

## Root cause of "anthropic endpoint not working"

The Anthropic surface was `https://inference.vulcan.alliancecan.ca/anthropic/v1/...`
(`docs/ENDPOINTS.md`: "`/v1/messages` (also `/anthropic/v1/messages`)"). The `/anthropic/`
prefix was served by a Tyk API definition that existed only on the OLD cluster — added live,
never committed. The cluster was rebuilt ~Aug 24 from
`ww-overlays/overlays/control-plane/etc/rancher/manifests/53-tyk-api-definitions.yaml`,
which contains only two API definitions:

- `model-gateway` — listen `/v1/`, keyed (Bearer; JSVM normalizeAuth accepts x-api-key etc.)
- `model-web` — listen `/`, keyless (landing page, /healthz, /metrics)

So `/anthropic/v1/messages` now falls through the keyless `/` API with the prefix
un-stripped, hits FastAPI, and returns `{"detail":"Not Found"}` 404.

Verified live 2026-08-25:
- `POST /anthropic/v1/messages` → 404 `{"detail":"Not Found"}` (FastAPI default = reached gateway un-stripped)
- `POST /v1/messages` directly with model `gpt-oss-120b` → 200, correct Anthropic response shape

Secondary issues found (worth fixing in the same pass, via CI):
1. `POST /v1/messages/count_tokens` (Claude Code calls it on every session) has no handler.
   It falls into the `/v1/{path:path}` catch-all (`forward_custom`), which pops `model` for
   cards with `custom_params.passthrough: true` (gpt-oss-120b has it) → vLLM 400
   "body.model Field required". Verified live.
2. `GET /v1/models` shows Anthropic clients all 21 chat models (13 are scale-to-zero) in
   OpenAI shape. Desired: Anthropic clients see ONLY always-on chat LLMs, in Anthropic list
   shape. The always-on set changes often — it MUST be evaluated live from model cards,
   never hardcoded.
3. `/metrics` counters live in process memory of each of the 3 replicas, so consecutive
   scrapes through the LB return different numbers (observed `gateway_requests_total` 3687
   then 3206). `usage.py` also counts per-model `errors` and `total_tokens` that `/metrics`
   never emits, and there are no per-model `scaled_up`/`replicas` gauges.
4. Per-key Tyk rate limit is 60 req/60s (commit `275eda9`). Claude Code bursts parallel
   requests and will 429 at 60/min. Precedent: the RagFlow key (`ragflow-vulcan-general-key`)
   was raised live to 600/60 on 2026-08-25 (survives rebuilds — keys live in Tyk redis on
   the nfs-models PVC).

---

## Part 1 — Restore the /anthropic Tyk route (the regression; do this first)

Add a third API definition `model-anthropic`: listen `/anthropic/`, **strip_listen_path
true**, same target and keyed auth + JSVM middleware as `model-gateway`. Tyk
longest-prefix-matches, so `/anthropic/` wins over `/`. It also injects
`X-Aleph-Api: anthropic` so the gateway can detect the Anthropic surface (used in Part 2a).

Commit it in BOTH places (the repo convention — see the header of 53-tyk-api-definitions.yaml):
- new key `model-anthropic.json` in the ConfigMap in
  `ww-overlays/overlays/control-plane/etc/rancher/manifests/53-tyk-api-definitions.yaml`
- mirror file `gateway/tyk/model-anthropic-api.json`

```json
{
  "name": "model-anthropic",
  "slug": "model-anthropic",
  "api_id": "model-anthropic",
  "org_id": "orgid",
  "use_keyless": false,
  "use_standard_auth": true,
  "auth": { "auth_header_name": "Authorization" },
  "version_data": {
    "not_versioned": true,
    "versions": {
      "Default": {
        "name": "Default",
        "use_extended_paths": true,
        "global_headers": { "X-Aleph-Api": "anthropic" }
      }
    }
  },
  "proxy": {
    "listen_path": "/anthropic/",
    "target_url": "http://model-gateway.models.svc.cluster.local:80",
    "strip_listen_path": true
  },
  "custom_middleware": {
    "driver": "otto",
    "pre":  [ { "name": "normalizeAuth", "path": "/opt/tyk-gateway/middleware/normalizeAuth.js", "require_session": false } ],
    "post": [ { "name": "injectIdentity", "path": "/opt/tyk-gateway/middleware/injectIdentity.js", "require_session": true } ],
    "auth_check": { "name": "" }, "post_key_auth": [], "response": []
  },
  "active": true,
  "enable_context_vars": true,
  "do_not_track": false,
  "disable_rate_limit": false,
  "disable_quota": true
}
```

Live apply (no rebuild needed):
```bash
kubectl apply -f ww-overlays/overlays/control-plane/etc/rancher/manifests/53-tyk-api-definitions.yaml
kubectl rollout restart deploy/gateway-tyk-oss-tyk-gateway -n tyk
```

### Key grants — REQUIRED or keyed calls get 403

Existing keys only carry `access_rights["model-gateway"]`; the new api_id needs granting.

- New keys: add a `model-anthropic` block to `access_rights` in BOTH
  `ww-overlays/overlays/control-plane/usr/local/bin/tyk-admin.sh` (the day-2 tool; keep the
  nested rate/per fields it sets per commit `275eda9`) and `gateway/tyk/tyk-keys.sh`.
- Existing keys, one-off migration (keys persist in Tyk redis on the nfs-models PVC):
  ```
  GET  /tyk/keys                       -> list hashes
  GET  /tyk/keys/<hash>?hashed=true    -> session JSON
  add access_rights["model-anthropic"] mirroring the key's model-gateway block (same rate/per)
  PUT  /tyk/keys/<hash>?hashed=true&suppress_reset=1
  ```
  Gateway admin API: `http://172.26.92.43:30808` (NodePort) or the tyk pod ClusterIP
  (`http://10.42.0.30:8080` as of 2026-08-25), header `X-Tyk-Authorization: $TYK_GW_SECRET`.
  Secret source: `kubectl get secret -n tyk secrets-tyk-oss-tyk-gateway -o jsonpath='{.data.APISecret}' | base64 -d`
  (also readable from the tyk process env: `pgrep -f tyk-gateway`, `/proc/<pid>/environ`).
- Rate limits: keys used by coding agents (Claude Code) should be >=300/60s. Bump the
  specific key's `rate` (top-level AND nested in each access_rights block — Tyk enforces the
  nested one) with `PUT ?suppress_reset=1`; distributed limiter settles in ~1 min.

## Part 2 — Gateway changes (`gateway/app/gateway.py` only, shipped via CI)

### 2a. Anthropic-aware model list
In `list_models()` (`@app.get("/v1/models")`, ~line 1482): when the request is
Anthropic-surface — header `X-Aleph-Api: anthropic` (from the new Tyk def) OR
`anthropic-version` present — return only chat models that are declared always-on, in
Anthropic list shape. Otherwise behavior is EXACTLY unchanged (incl. `?all=true`).

- Always-on predicate, live from the card each request (no hardcoded model ids):
  `not scaling.scale_to_zero and (min_replicas is None or int(min_replicas) >= 1)`
- Anthropic shape: `{"data": [{"type": "model", "id": ..., "display_name": ..., "created_at": ...}],
  "has_more": false, "first_id": ..., "last_id": ...}`, sorted by id.
- Do NOT change `/v1/messages` request gating — any chat model stays callable (pre-rebuild behavior).
- Snapshot of the always-on set today (8) — for verification only, never hardcode:
  aya-expanse-8b, gemma-4-26b-a4b, gpt-oss-120b, gpt-oss-20b, phi-4-reasoning,
  qwen25-vl-72b-awq, qwen35-122b, tiny-aya-global.

### 2b. Dedicated count_tokens handler
Add `@app.post("/v1/messages/count_tokens")` ABOVE the `/v1/{path:path}` catch-all
(FastAPI matches in registration order):
- Resolve the model (`resolve()`); 404 unknown; 400 `anthropic_unsupported` for non-chat
  (same error shape `/v1/messages` uses).
- Rewrite `model` to `routing.upstream_model_id` when set (`_apply_upstream_model_id`),
  forward the body WITH `model` intact to `upstream_url("/v1/messages/count_tokens")` using
  `upstream_headers(info)`, return vLLM's `{"input_tokens": N}` verbatim.
- Never apply the `custom_params.passthrough` model-strip on this path (that's the bug).

### 2c. /metrics cluster-wide + missing series
- Fan-in: unless `?local=true`, list peer gateway pods via CoreV1
  `list_namespaced_pod(MODELS_NS, label_selector="app=model-gateway")` (pods get/list is
  already in the Role — no RBAC change), fetch `http://<pod_ip>:8080/metrics?local=true`
  from peers (skip self via `POD_NAME` env, already set in the Deployment), sum counter
  samples by (metric name, labels), serve the aggregate. Short timeout per peer; on any
  fetch error degrade to local-only rather than failing the scrape.
- Emit the counted-but-dropped series from `usage.snapshot()`:
  `gateway_model_errors_total`, `gateway_model_total_tokens_total`.
- Add live gauges: `gateway_model_scaled_up{model=...}` (0/1) and
  `gateway_model_replicas{model=...}` from the in-memory POD state.
- Counters still reset on pod restart; the durable feed remains the usage log on the RWX PVC.

## Part 3 — Ship it (LIVE SYSTEM: do not break OpenAI endpoints, audio, or streaming)

1. Commit `gateway/**` changes, push to `main`, wait for CI to publish
   `rkhoja/aleph:gateway-<newsha>` (~4 min, check Actions).
2. **Canary first — production untouched**: on aleph1 create a 1-replica
   `model-gateway-canary` Deployment (copy of live spec, new image, NO Service). Test the
   canary pod IP directly:
   - Repo battery: `cat gateway/test.py | kubectl exec -i -n models <canary-pod> -c gateway -- python3 -`
   - Streaming chat completions (`stream:true`, verify incremental SSE chunks)
   - `/v1/messages` non-stream + stream; `/v1/messages/count_tokens` → 200 with a count
   - `/v1/models` plain → byte-comparable to production; with `anthropic-version` header →
     filtered Anthropic shape
   - `/v1/embeddings` (bge-m3), `/v1/rerank` (bge-reranker-v2-m3)
   - `/v1/audio/transcriptions` (whisper multipart, incl. `stream=true`),
     `/v1/audio/speech` (kokoro → mp3)
   - `GET /` page renders; `/healthz`, `/readyz`, `/metrics?local=true`
3. Promote: commit the image tag bump in `ww-overlays/.../63-model-gateway.yaml`
   (MANDATORY — a rebuild resurrects whatever tag is pinned there), then
   `kubectl -n models set image deploy/model-gateway gateway=rkhoja/aleph:gateway-<newsha>`.
   RollingUpdate is maxSurge 1 / maxUnavailable 0 → zero downtime. Delete the canary.
4. Apply Part 1 (Tyk ConfigMap + restart + key migration) — order vs Part 3 doesn't matter,
   but both must be committed.
5. Rollbacks: gateway → `kubectl -n models set image deploy/model-gateway gateway=rkhoja/aleph:gateway-b37897c`;
   Tyk → remove `model-anthropic.json` from the ConfigMap, restart tyk deploy.

## Verify (through the public URL)

```bash
BASE=https://inference.vulcan.alliancecan.ca
KEY=<a granted tyk key>
# was 404 -> expect 200 Anthropic shape
curl -sS $BASE/anthropic/v1/messages -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01" \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-oss-120b","max_tokens":32,"messages":[{"role":"user","content":"say hi"}]}'
# was 400 -> expect {"input_tokens": N}
curl -sS $BASE/anthropic/v1/messages/count_tokens -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01" \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"hello"}]}'
# filtered Anthropic list (always-on chat models only)
curl -sS $BASE/anthropic/v1/models -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01"
# unchanged OpenAI list (21 chat entries; ?all=true full catalogue)
curl -sS $BASE/v1/models -H "Authorization: Bearer $KEY"
```

- Claude Code end-to-end: `ANTHROPIC_BASE_URL=$BASE/anthropic`,
  `ANTHROPIC_AUTH_TOKEN=<key>`, `ANTHROPIC_MODEL=gpt-oss-120b` — chat + token counting, no
  429 storm (bump the key's rate if needed).
- OpenAI regression through Tyk: streaming chat, whisper STT, kokoro TTS, embeddings,
  rerank — all unchanged.
- `/metrics` scraped twice in a row → identical, monotonic totals; new series present:
  `gateway_model_errors_total`, `gateway_model_total_tokens_total`,
  `gateway_model_scaled_up`, `gateway_model_replicas`.
