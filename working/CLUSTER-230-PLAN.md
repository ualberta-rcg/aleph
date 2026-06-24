# Cluster 230 — Build Plan

> The **how and when**. For architecture and card schema, see `GATEWAY-ARCHITECTURE.md`.
> Cluster 230 = `aleph1` (172.26.92.43), the new HAMi cluster.

## Where we are right now (verified 2026-06-04)

Cluster 230 is **further along than it looks** — the platform is up, only the gateway is missing.

| Component | State on 230 | Notes |
|---|---|---|
| RKE2 / nodes | ✅ control-plane + rack15-03 (4× L40S) | v1.36.1+rke2r2 |
| HAMi | ✅ `nvidia.com/gpu: 40` allocatable | 4 GPU × 10 split |
| KServe | ✅ controllers running | `kserve-controller-manager` 2/2 |
| Knative + Istio | ✅ running | `knative-local-gateway` up in istio-system |
| Tyk OSS + Redis | ✅ both running | gateway pod + `tyk-redis-master-0` |
| cert-manager / NFS / Traefik | ✅ running | |
| A model serving | ✅ `bge-small` (3/3) | proves the serving path end-to-end |
| **model-gateway** | ❌ **not deployed** | **← the work** |
| **details ConfigMaps** | ❌ none on 230 | none migrated yet |
| External domain / TLS | ❌ not wired | Phase 4 |

**What this means:** we don't need to stand up infrastructure. We need to **build the gateway**
(the card-reading one that never existed) and prove it against the one model already running.

## Build log — Phase 1 done (2026-06-04)

The card-driven gateway is built, deployed, and behind Tyk. Source lives in this repo under
`gateway/` (app, Dockerfile, k8s manifests, cards, tyk API def) and `models/` (per-model
ISVC + card).

| Item | State | Notes |
|---|---|---|
| `model-gateway` | ✅ running in `models` (2/2, Istio sidecar) | card-driven, K8s Watches, no hardcoded models |
| Image | ✅ `model-gateway:0.2` built with Docker on the control-plane VM, imported into RKE2 containerd; `imagePullPolicy: Never`, pinned to head node | no registry yet; see build gotcha |
| RBAC | ✅ adds `configmaps get/list/watch` (the POC lacked this) | required to read cards |
| bge-small card | ✅ embeddings proven through gateway + Tyk | first real card |
| command-r-7b | ✅ ported from POC, HAMi-adapted (sub-GPU vGPU slice) | first GPU model on 230 |
| OpenAI endpoints | ✅ `/v1/chat/completions`, `/v1/embeddings`, `/v1/models` | |
| Anthropic endpoint | ✅ `/v1/messages` (native), stream + non-stream | `app/anthropic_xlate.py` translator |
| Response `resources` block | ✅ gpus/vram/cpu/ram (from ISVC spec) + `latency_ms` | next to `usage`; live GPU util = future (DCGM) |
| Tyk `model-gateway` API | ✅ token auth, proxying to `model-gateway.models:80` | see Tyk gotcha below |
| External access | ✅ NodePort `30808` on the host IP | `gateway/tyk/nodeport.yaml` |

### Build gotcha — import into RKE2's containerd, not the host's

The host runs **two** containerds: the system/Docker one (`/run/containerd/containerd.sock`)
and **RKE2's** (`/run/k3s/containerd/containerd.sock`). Only RKE2's is used by the kubelet.
`docker save model-gateway:0.2 | ctr -n k8s.io images import -` defaults to the *host* socket,
so the pod fails with `ErrImageNeverPull`. Always pass the RKE2 socket:

```bash
docker build -t model-gateway:0.2 .
docker save model-gateway:0.2 | \
  /var/lib/rancher/rke2/bin/ctr --address /run/k3s/containerd/containerd.sock -n k8s.io images import -
# verify: ctr --address /run/k3s/containerd/containerd.sock -n k8s.io images ls | grep model
kubectl set image deploy/model-gateway -n models gateway=model-gateway:0.2   # container name is "gateway"
```

### Known issue — NFS (`nfs-client`) fails large writes with EIO

Found while migrating command-r-7b. The default StorageClass `nfs-client`
(`manage.storage.data.vulcan.local:/kubeflow`) has **3.3 PB free** but **any multi-GB write
fails with `OSError: [Errno 5] Input/output error`** — small JSON files write fine, a 2 GB `dd`
fails at 0 bytes. So model weights cannot be staged on a PVC right now.

- **Workaround in use:** command-r-7b stages weights on a local **`emptyDir`** on rack15-03
  (re-downloads ~15 GB on every pod restart). See `models/command-r-7b/inferenceservice.yaml`.
- **To fix properly:** debug the NFS server/export (mount options `wsize`/`rsize`, sync vs async,
  underlying storage health) so PVCs can hold weights and we stop re-downloading. The
  `pvc.yaml` is kept in the repo for when NFS is fixed.

### command-r-7b — HAMi vGPU verified

First GPU model on 230, ported from the POC. Requests `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 24576`
(half an L40S = sub-GPU slice). **HAMi confirmed working:** `nvidia-smi` *inside* the pod reports
`24576 MiB` total VRAM (not the physical 48 GB) and the `HAMI-core` memory limiter logs on exit.
End-to-end proven: `Client → Tyk (key) → model-gateway → KServe/vLLM` returns completions; no key → 401.

### Response telemetry — `resources` block

Every non-streaming chat / embeddings / messages response (and the final Anthropic
`message_delta` for streams) now carries a `resources` block next to the token `usage`:

```json
"usage": { "prompt_tokens": 11, "completion_tokens": 11, "total_tokens": 22 },
"resources": {
  "model": "command-r-7b",
  "gpus": 1, "vram_mib": 24576, "cpu_cores": 4.0, "system_ram_mib": 16384,
  "latency_ms": 372
}
```

- `gpus / vram_mib / cpu_cores / system_ram_mib` are the **allocated footprint**, read live from
  the InferenceService predictor spec (single source of truth — no duplication in the card).
- `latency_ms` is measured in the gateway around the upstream call.
- **Not yet:** live GPU **utilization %**, instantaneous VRAM in use, GPU index/UUID, and node
  name. Those need a metrics source (DCGM exporter or the HAMi metrics endpoint); wire that in to
  populate `gpu_util_pct` / `vram_used_mib` later. Open item.

### Tyk gotcha — APPPATH pointed at an empty scratch dir

Tyk OSS (Helm `tyk-oss`) was running with **0 APIs** the whole time. The `setup-directories`
initContainer only does `mkdir -p apps middleware policies` inside the `tyk-scratch` emptyDir
mounted at `/mnt/tyk-gateway`, and `TYK_GW_APPPATH=/mnt/tyk-gateway/apps` pointed there — empty.
The API-definitions ConfigMap (`tyk-api-definitions`) is mounted **separately** at
`/opt/tyk-gateway/apps` and was never read.

Fix applied: `kubectl set env deploy/gateway-tyk-oss-tyk-gateway -n tyk TYK_GW_APPPATH=/opt/tyk-gateway/apps`
so Tyk reads API defs straight from the ConfigMap mount. After this it logged
`Loading API Specification from /opt/tyk-gateway/apps/model-gateway.json` → `Detected 1 APIs`.

> This env override is a patch on a Helm-managed Deployment. **Move it into the Helm values**
> (`tyk-gateway.gateway.extraEnvs` or the chart's `appPath`) so a chart upgrade doesn't revert it.

To update the API def: edit ConfigMap `tyk-api-definitions` (source = `gateway/tyk/model-gateway-api.json`)
and `kubectl rollout restart deploy/gateway-tyk-oss-tyk-gateway -n tyk`.

### Tyk key management (OSS REST API)

The Tyk gateway REST API is authenticated with header `x-tyk-authorization: <APISecret>`
(`secret/secrets-tyk-oss-tyk-gateway` key `APISecret`). Keys live in Redis, so they persist
and work in file-based mode. Keys only take effect when the API is **protected**
(`use_keyless: false`, `use_standard_auth: true`).

| Action | Call (against `gateway-svc-tyk-oss-tyk-gateway.tyk:8080`) |
|---|---|
| Create key | `POST /tyk/keys/create` with `{"alias","access_rights":{"model-gateway":{"api_id":"model-gateway","api_name":"model-gateway","versions":["Default"]}}}` |
| List keys | `GET /tyk/keys` |
| Inspect key | `GET /tyk/keys/<keyId>` |
| Revoke key | `DELETE /tyk/keys/<keyId>` |

Client then calls the API with `Authorization: Bearer <keyId>` — Tyk strips the `Bearer `
prefix, so it is OpenAI-SDK compatible (also accepts the raw key).

**Verified lifecycle (2026-06-04):** no key → `401`; valid key → `200`; after `DELETE` → `403`.
Note: Tyk keeps an in-memory **session cache (~10s)**, so a revoked key may keep working for a
few seconds until the cache expires — expected, not a bug.

## Accessing the gateway from the login nodes (NodePort + PAM/Tyk)

No public IP / LoadBalancer, but the login nodes are on the same internal network as node 230,
so a **NodePort** on the head-node IP is enough.

```
login node  ──HTTP──>  172.26.92.43:30808  ──>  Tyk (auth/keys)  ──>  model-gateway  ──>  KServe/vLLM
            (any internal client)            NodePort           ClusterIP         (cards)      (GPU pods)
```

- **Endpoint:** `http://172.26.92.43:30808` (Service `tyk-gateway-nodeport`, `gateway/tyk/nodeport.yaml`).
  The NodePort is open on **every** node's IP, but use a **control-plane VM IP** (currently the
  head node `172.26.92.43`), not the GPU worker.
- OpenAI SDK: `base_url="http://172.26.92.43:30808/v1"`, `api_key=<tyk key>`.
- Anthropic SDK: `base_url="http://172.26.92.43:30808"` (it appends `/v1/messages`), `api_key=<tyk key>`.

### Topology / placement

- **Gateway pinned to control-plane (non-GPU) nodes** via `nodeSelector
  node-role.kubernetes.io/control-plane: "true"` + nodeAffinity `gpu NotIn [on]`
  (`gateway/k8s/deployment.yaml`). It never runs on GPU workers, so it can't steal resources
  from model pods. Tyk + Redis already live on the control plane too.

### Future: 3 control-plane VMs

When the control plane grows to 3 VMs:
1. **Stable endpoint (no SPOF):** a single node IP is a single point of failure. Put a **VIP**
   in front of the 3 control-plane VMs (kube-vip or keepalived) and point clients/DNS at the VIP
   (e.g. `gateway.vulcan.local:30808`, or front it with Traefik on `:80/:443` for a clean name).
2. **Image distribution:** with `imagePullPolicy: Never`, the gateway image must exist on whichever
   CP VM it schedules onto. Either import `model-gateway:<tag>` into RKE2 containerd on **all 3**
   CP VMs, or (better) **stand up an in-cluster registry** and switch to `imagePullPolicy: IfNotPresent`.
3. **Replicas:** bump `model-gateway` to `replicas: 3` (it's stateless — all state is in K8s
   ConfigMaps/ISVCs via watches) so it tolerates losing a CP VM. Tyk likewise scales horizontally
   (state in Redis).

Working curl (replace the key):

```bash
curl http://172.26.92.43:30808/v1/chat/completions \
  -H "Authorization: Bearer <TYK_KEY>" -H "Content-Type: application/json" \
  -d '{"model":"command-r-7b","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'

# Anthropic-native:
curl http://172.26.92.43:30808/v1/messages \
  -H "Authorization: Bearer <TYK_KEY>" -H "Content-Type: application/json" \
  -d '{"model":"command-r-7b","max_tokens":40,"messages":[{"role":"user","content":"hi"}]}'
```

### Tyk keys ↔ usernames (for PAM scripts)

Tyk OSS has no separate "user" object, but **every key carries identity** via `alias` (human
label) and `meta_data` (arbitrary map). A PAM script issues one key per user and stamps the
username/uid/account on it. The key string is the bearer token the user puts in their client.

```bash
TYK=http://172.26.92.43:30808
SECRET=$(kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk -o jsonpath='{.data.APISecret}' | base64 -d)
# (run the kubectl on node 230, or cache the secret in the PAM script's config)

# Issue a key bound to a user (Tyk generates the key string):
curl -s -X POST $TYK/tyk/keys/create -H "x-tyk-authorization: $SECRET" -H "Content-Type: application/json" -d '{
  "alias": "rahimk",
  "meta_data": {"username": "rahimk", "uid": "100123", "account": "def-pi", "source": "pam"},
  "tags": ["pam", "vulcan-login"],
  "access_rights": {"model-gateway": {"api_id": "model-gateway", "api_name": "model-gateway", "versions": ["Default"]}}
}'
# -> {"key":"<TYK_KEY>","key_hash":"...","status":"ok","action":"added"}
```

All calls go to `http://172.26.92.43:30808/tyk/...` with header `x-tyk-authorization: <APISecret>`.
The admin `APISecret` is `tyk-oss-cluster-secret-2026` (`secret/secrets-tyk-oss-tyk-gateway`).

| Action | Call |
|---|---|
| Issue key for a user | `POST /tyk/keys/create` (body above; `meta_data.username` = the user) |
| Deterministic key id | `POST /tyk/keys/<your-id>` (same body) — you choose the token, e.g. derive from uid |
| List all keys | `GET /tyk/keys` → `{"keys":[<hash>,...]}` (hashes, not raw tokens) |
| Inspect by raw key | `GET /tyk/keys/<key>` (shows `alias`, `meta_data`, `access_rights`) |
| Inspect by hash | `GET /tyk/keys/<hash>?hashed=true` (use the hashes from the list) |
| Update a key | `PUT /tyk/keys/<key>` (re-send full body to change quota/rate/meta) |
| Revoke by raw key | `DELETE /tyk/keys/<key>` |
| Revoke by hash | `DELETE /tyk/keys/<hash>?hashed=true` (effective after the ~10s session cache) |

Helper script: `gateway/tyk/tyk-keys.sh {list|create <user> [uid] [account]|inspect <hash>|revoke <hash>|test <key>|find <user>|revoke-user <user>}`.

**List / revoke by username:** Tyk OSS has **no username index** — `GET /tyk/keys` only returns
hashes. So `find <user>` and `revoke-user <user>` *scan*: list hashes → `GET /tyk/keys/<hash>?hashed=true`
→ filter on `meta_data.username` → (for revoke-user) `DELETE` each match. Verified: created 2 keys
for `carol`, `find carol` showed both, `revoke-user carol` deleted both. This is O(n) over all keys —
fine for modest counts. For large fleets, keep your own username→key index in the PAM layer, or use
deterministic key ids (`POST /tyk/keys/<id-derived-from-username>`) so revoke is a direct `DELETE`.

> **Listing had to be enabled.** Tyk OSS disables key listing by default
> (`Hashed key listing is disabled in config`). Enabled via
> `kubectl set env deploy/gateway-tyk-oss-tyk-gateway -n tyk TYK_GW_ENABLEHASHEDKEYSLISTING=true`.
> Like the APPPATH override, this is a patch on a Helm-managed Deployment — **move it into the
> Helm values** (`tyk-gateway.gateway.extraEnvs`) so a chart upgrade keeps it.

Notes for PAM integration:
- `GET /tyk/keys` returns **hashes** by default (raw tokens aren't recoverable) — so the PAM
  script must store the key string it gets back at create time (or use deterministic key ids).
- Per-user **rate limit / quota** go in `access_rights.model-gateway.limit` (e.g. `rate`, `per`,
  `quota_max`, `quota_renewal_rate`) or at the key root.
- To get the username **into the gateway/model logs** for per-user accounting, add a Tyk header
  transform that injects `$tyk_meta.username` as an upstream header (e.g. `X-User`). Not wired yet —
  open item if we want per-user usage attribution at the model layer.
- The admin secret (`APISecret`) is the root credential — keep it on the login node's PAM config
  with tight perms; don't hand it to users.

## Source material on the POC (232)

Reuse, don't reinvent. On `172.26.92.232:/root/kuberflow-working/`:

- `gateway/gateway.py` (2072 lines) — the **logic to port** (handlers, protocol conversion,
  meta-task detection, streaming). Strip the ~12 hardcoded dicts; keep the request-handling guts.
- `models/*/details.yaml` — **157 real cards** to migrate (already labelled `model-details: "true"`).
- `models/*/inferenceservice.yaml` — ISVC manifests to convert GPU-operator → HAMi format.
- `MODEL-DETAILS-SYSTEM.md`, `MODELS.md` — the original design + model inventory.

## Phase 1 — Gateway core (START HERE)

**Goal:** a rock-solid, card-driven gateway running on 230, proven against `bge-small`, before
any auth/models/external access. This is the only phase that needs careful design.

### 1.1 — Card loader + discovery (the part the POC never built)
- [ ] `discover()`: on startup, `list` ISVCs + `model-details` ConfigMaps → build routing table.
- [ ] K8s **Watch** on both (CoreV1 ConfigMaps + KServe custom objects) → live updates, no polling.
- [ ] Merge: card = base, ISVC = host/ready/replicas, model `/v1/models` = runtime supplement.
- [ ] RBAC: ServiceAccount with `get/list/watch` on configmaps + inferenceservices in `models`.
- [ ] **Zero hardcoded model names.** If a model name appears in code, it's a bug.

### 1.2 — Port handlers from POC `gateway.py` (drop the dicts)
Handlers are selected by **path family**, NOT card `type` (POC lesson — see `GATEWAY-ARCHITECTURE.md`).
Port the full set, not just the chat core:
- [ ] `chat` → apply defaults + `param_translation`, forward to vLLM/llama.cpp.
- [ ] `embeddings` → TEI ↔ OpenAI reshape (test target: **bge-small**, already running).
- [ ] `rerank` → Cohere/Jina ↔ TEI.
- [ ] `audio` → `/v1/audio/transcriptions` (multipart→JSON, STT), `/v1/audio/speech` (JSON→raw
      bytes, TTS), `voices`/`clone`. Needs `routing.upstream_model_id` remap (whisper, kokoro).
- [ ] `vision` → `/v1/vision/{classify,embed,detect,segment,depth,face}` with per-task default model.
- [ ] `science` → `/v1/science/*`, `/v1/design`, `/v1/dock` + `/v1/{custom}` catch-all that
      **forwards** to the model's own `server.py` (esmfold `/v1/structure`, etc.). First-class, register last.
- [ ] `anthropic` (`/v1/messages`, native Anthropic SDK path) → thin wrapper, NOT a parallel
      build: register before the `/v1/{custom}` catch-all; convert Anthropic→OpenAI, run the same
      card pipeline, convert response + SSE back. Common chat core only — drop unsupported
      Anthropic fields (cache_control, citations, documents), `400` on server-side tools
      (web_search/code_execution). See parity matrix in `GATEWAY-ARCHITECTURE.md`.
- [ ] `forward` → pass-through for science models.
- [ ] Meta-task detection → `defaults.meta_tasks` (no hardcoded reasoning branches).

### 1.3 — Deploy
- [ ] FastAPI Deployment + Service in `models` ns, Istio sidecar (reach knative-local-gateway).
- [ ] `/healthz` (discovery loop alive) + `/readyz` (≥1 card loaded).
- [ ] Limits 256Mi / 500m. Stateless → scalable to N replicas later.
- [ ] Graceful shutdown: drain in-flight + finish streams.

### 1.4 — Reliability
- [ ] Request timeout per card (`deployment.timeout`, default 300s).
- [ ] Scale-to-zero handling: 503 + ETA from `deployment.startup_seconds`.
- [ ] httpx connection pooling per upstream host.
- [ ] Per-model semaphore when `routing.serialize: true`.
- [ ] SSE streaming with backpressure.
- [ ] One JSON log line per request (model, user, tokens, latency, status).

### 1.5 — Metrics (endpoint only, no Prometheus on this cluster)
- [ ] `/metrics` Prometheus format: requests_total, tokens_*, request_duration, models_ready.

**Phase 1 exit criteria**
- `curl` (in-cluster) to gateway `/v1/embeddings` hits `bge-small` and returns embeddings.
- Deploy a second card → appears in `/v1/models` within seconds, **no gateway restart**.
- Delete a card → disappears. No model names anywhere in the gateway source.

## Phase 2 — Auth + key management (separate design pass)

Card-driven gateway is the safe part; **auth is the risky part — design it on its own** before
writing the `profile.d` script. Sketch only:

- Tyk key per user, `alias = LDAP username`. LDAP used **once** at key creation, never per-request.
- Vulcan users: `/etc/profile.d` script (Warewulf overlay) provisions key on login → `$HOME/.inference_api_key` on NFS.
- `inference-key` CLI (self-service + admin) over Tyk REST API.
- Remote/non-Vulcan users: admin-created keys, or optional `/auth/register` LDAP-bind endpoint.

⚠️ **Review before building:** admin secret distribution (Warewulf overlay vs K8s Secret),
public LDAP-bind endpoint exposure, secret-on-every-login. Don't ship the bash snippet from
`GATEWAY-DESIGN.md` as-is.

## Phase 3 — Usage logging (no monitoring stack)

- Gateway JSON logs to stdout (K8s captures) — per-request user/model/tokens/gpu/duration.
- GPU-hours computed **in reporting**, not in logs: `gpu_hours = (ms/3.6e6) × physical_gpu_count × (hami_vram_mb / per_card_vram)`.
- Tyk analytics already in Redis (`tyk-redis-master-0`) — query for path/status/latency/user.
- `inference-usage-report --day` script on a login node → CSV for Alliance reporting.
- `/metrics` stays ready for whenever Prometheus gets a home (not here).

## Phase 4 — External access

- Traefik IngressRoute `api.vulcan.alliancecan.ca` → Tyk → `model-gateway.models.svc:80`.
- TLS via cert-manager (DNS-01) or manual cert. DNS → cluster external IP.
- Smoke test: `curl https://api.vulcan.alliancecan.ca/v1/models -H "Authorization: Bearer $KEY"`.

## Phase 5 — Migrate models from POC (232 → 230)

POC cluster will be **destroyed** and its nodes Warewulf-reprovisioned into 230 (target: 20× L40S).
So this is a migration, not parallel running.

**Per-model checklist:**
1. [ ] **Trim + extend** the existing `details.yaml`: drop K8s-duplicated fields (`server_config`,
      `deployment.gpu*`, `container_image`, `node`) and runtime-derivable ones (`context_window`),
      move catalog text (`description`, `license`, `tags`, `input_map`/`output_map`) into an
      optional `catalog` block, then add the 3 behavior sections (`param_translation`,
      `defaults`, `custom_params`). Bump `schema_version`. Net: card shrinks ~⅔.
      See "Trim the card" in `GATEWAY-ARCHITECTURE.md`.
2. [ ] Convert ISVC GPU format: `nvidia.com/gpu.product` selector → `gpu: "on"` label + `nvidia.com/gpu` + `nvidia.com/gpumem`.
3. [ ] `kubectl apply` ISVC + card → gateway auto-discovers.
4. [ ] Verify routing + response.

**Order:** CPU models → single-GPU → multi-GPU → science models.

**Card migration is bulk-scriptable:** 157 cards share the v1 schema; the 3 new sections can be
templated per `type` and per thinking `mode`, then hand-tuned for the reasoning models.

## GPU format conversion cheatsheet (POC → HAMi)

| | POC (232, GPU Operator) | 230 (HAMi) |
|---|---|---|
| Node select | `nvidia.com/gpu.product: NVIDIA-L40S` | label `gpu: "on"` |
| Whole GPU | `nvidia.com/gpu: 4` | `nvidia.com/gpu: 4` + `nvidia.com/gpumem: 46068` |
| Shared slice | n/a | `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 10240` |
| Slicing | operator time-slice config | HAMi `deviceSplitCount: 10` |

## Sequence

```
Phase 1  Gateway core (card loader + handlers + bge-small proof)   ← DO FIRST
Phase 2  Auth (design pass before code)
Phase 3  Usage logging (JSON + Redis)
Phase 4  External access (domain + TLS)
Phase 5  Migrate 157 cards + ISVCs from POC
```

Phases 1–3 are fully testable in-cluster with `curl` pods. Phase 4 opens it up. Phase 5 scales out.

## Immediate next actions

1. Pull `gateway.py` + a few `details.yaml` from 232 into `~/hami-cluster-test/gateway/` to work from.
2. Build the **card loader + Watch** first (1.1) — it's the keystone the POC never had.
3. Prove it against `bge-small` (already running) before porting the rest of the handlers.
