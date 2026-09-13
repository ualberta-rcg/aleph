# Operations Guide — Model Inference Gateway

How to stand up and operate the card-driven model inference gateway: a FastAPI gateway
(card routing + OpenAI/Anthropic translation) fronted by **Traefik/TLS + Tyk** (token auth), serving
models on **HAMi** fractional GPUs via **KServe/Knative**. This is a **manual, step-by-step**
guide so it can be reproduced on **any** equivalent cluster.

> **Cluster-specific values** (IPs, hostnames) are **not committed here**. The table in
> §0 uses placeholders; fill them in for your cluster.
>
> Companion docs (this repo): [`../TYK-USERS.md`](../TYK-USERS.md) (keys/identity),
> [`../LOGGING.md`](../LOGGING.md) (usage ledger), [`gateway/README.md`](../gateway/README.md)
> (gateway internals + card schema). The platform manifests (RKE2 auto-deploy + WW
> overlay) live in [`ww-overlays/`](../ww-overlays/).

---

## Architecture at a glance

```
client ──HTTPS──> https://<public-hostname>
              ──> <VIP> (MetalLB) ──> Traefik rke2-traefik-public (TLS, Let's Encrypt)
              ──> Tyk (token auth/keys, Redis; ClusterIP) ──> model-gateway (cards)
                                                                       │
                                            ┌──────────────────────────┴────────────────────────────┐
                                            ▼ (Knative local gateway, Host: <isvc>-predictor)        ▼ (same, custom /v1/* paths)
                                       KServe ISVC predictors — chat / embed / science         media backends (image gen, TTS)
                                            ▼
                                       HAMi vGPU slices on GPU workers (label gpu=on)
```

- **Gateway** is pinned to control-plane (non-GPU) nodes; it never steals resources from model pods.
- **One plane, all ISVCs**: *every* model — chat, science, embed, media — runs as a Knative
  `InferenceService`. The only non-Knative Deployment in the `models` ns is model-gateway
  itself.
- **Cards are the single source of model truth.** The gateway reads them at runtime — adding a
  model = apply an ISVC + a card ConfigMap, **zero gateway changes, zero restart**.

---

## 0. Per-cluster values to substitute

Find these on the target cluster first; every command below references them.

| Placeholder | What it is | How to find it |
|---|---|---|
| `VIP` | MetalLB public VIP (Traefik TLS edge, port 443) | `kubectl get svc rke2-traefik-public -n kube-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}'` |
| `GW_URL` | public endpoint hostname | `https://inference.vulcan.alliancecan.ca` (the live deployment) |
| `GPU_NODE` | a GPU worker hostname | `kubectl get nodes -l gpu=on` |
| GPU node label | label HAMi device-plugin keys on | `gpu=on` (applied automatically by `09-gpu-autolabel` — see gotcha #10) |
| CP node label | control-plane selector | `node-role.kubernetes.io/control-plane=true` |
| `TYK_DEPLOY` | Tyk gateway Deployment | `kubectl get deploy -n tyk` (Helm default `gateway-tyk-oss-tyk-gateway`) |
| `TYK_SECRET` | Tyk admin `APISecret` | `kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk -o jsonpath='{.data.APISecret}' \| base64 -d` |
| Tyk APPPATH mount | where the `tyk-api-definitions` CM is mounted | `/opt/tyk-gateway/apps` |
| StorageClass | default SC | `kubectl get sc` (⚠️ see NFS gotcha #4) |
| RKE2 containerd sock | socket `ctr` must talk to | `/run/k3s/containerd/containerd.sock` (RKE2 default) |

Keep your site's literal values outside this repo (gitignored `.env` / site notes).

---

## Prerequisites — verify the built-ins are healthy

**Everything installs from the numbered RKE2 auto-deploy manifests** baked into the
Warewulf control-plane overlay (`ww-overlays/overlays/control-plane/etc/rancher/manifests/`,
00→80 — see [`ww-overlays/README.md`](../ww-overlays/README.md)). Provision/boot the WW nodes and the
whole platform (cert-manager, HAMi, NFS, MetalLB+VIP, Traefik, Tyk+Redis, Istio,
Knative, KServe, model-gateway) comes up. There is no installer script — the overlay
set is the installer.

```bash
kubectl get nodes -l gpu=on                # GPU workers (auto-labeled by 09-gpu-autolabel)
kubectl get node <GPU_NODE> -o jsonpath='{.status.allocatable}' | tr ',' '\n' | grep nvidia  # nvidia.com/gpu: N (10 × physical cards)
kubectl get pods -n kube-system | grep -i hami                                       # hami-scheduler + device-plugin
kubectl get sc                             # nfs-models default (verify mountOptions — gotcha #4)
kubectl get pods -n cert-manager           # cert-manager up
kubectl get deploy -n tyk                  # gateway-tyk-oss-tyk-gateway
```

---

## 1. Gateway image (Docker Hub — auto-deployed)

CI publishes the gateway to **`rkhoja/aleph`** on Docker Hub on every push to `main` touching
`gateway/**` (workflow: `.github/workflows/deploy-gateway.yml`). Tags: moving `latest` and
immutable `gateway-<shortsha>`.

The Deployment (`ww-overlays/overlays/control-plane/etc/rancher/manifests/63-model-gateway.yaml`)
is part of the WW overlay auto-deploy set — it comes up automatically when the cluster boots.
To roll out a new build after a push, **pin it — never roll `:latest` in prod**:

```bash
# 1. Bump the image pin in 63-model-gateway.yaml (repo copy AND on all CP nodes — keep in sync)
# 2. Apply the new tag:
kubectl set image deploy/model-gateway -n models gateway=rkhoja/aleph:gateway-<sha>
kubectl rollout status deploy/model-gateway -n models
```

(`imagePullPolicy: IfNotPresent` — a bare `rollout restart` does NOT pull a new build.)

## 2. Gateway RBAC + Service + Deployment

**Auto-deployed** by `ww-overlays/overlays/control-plane/etc/rancher/manifests/63-model-gateway.yaml` as part
of the RKE2 auto-deploy set. No manual apply needed on a fresh cluster.

Key deployment choices (from `gateway/k8s/deployment.yaml`, now baked into `63-model-gateway.yaml`):
- **Pinned to control-plane / non-GPU nodes:** `nodeSelector node-role.kubernetes.io/control-plane: "true"`
  + nodeAffinity `gpu NotIn [on]`. Keeps it off GPU workers; covers all CP VMs.
- `image: rkhoja/aleph:gateway-<sha>` — immutable pin from Docker Hub (`imagePullPolicy: IfNotPresent`).
- **3 replicas** (sized for ~200 concurrent users; podAntiAffinity across CP nodes).
- Usage-log PVC `model-gateway-usage-logs` mounted at `/var/log/aleph` (per-replica subPath).
- Istio sidecar via pod label `sidecar.istio.io/inject: "true"`.

The gateway needs at least one card applied (next step) before `/readyz` goes green.

## 3. Model cards (the discovery mechanism)

Cards are ConfigMaps labelled `model-details=true`, containing `details.json`. The gateway
watches them — **no restart needed to add a model.**

```bash
kubectl apply -f gateway/cards/                       # e.g. bge-small
kubectl apply -f models/command-r-7b/details.yaml     # a GPU model's card
```

Card schema: [`models/DETAILS-TEMPLATE-LLM.md`](../models/DETAILS-TEMPLATE-LLM.md) (templates) and
[`gateway/README.md`](../gateway/README.md) (which fields the gateway reads). Minimal core: `id`, `type`,
`endpoints.primary`, `routing`, `limits`, `behavior`, `param_translation.thinking`, `defaults`.
Everything else (`catalog`, `input_map`, `output_map`) is documentation/catalog only — not read
by the gateway routing path.

## 4. The GPU model on HAMi (worked example: `command-r-7b`)

Two changes vs a normal GPU-operator manifest, both in `models/command-r-7b/inferenceservice.yaml`:

1. **HAMi scheduling/limits** — instead of `nodeSelector nvidia.com/gpu.product=...`:
   ```yaml
   nodeSelector: { gpu: "on" }          # HAMi node label
   resources:
     limits:
       nvidia.com/gpu: "1"              # 1 vGPU slice
       nvidia.com/gpumem: "24576"       # 24 GB of a 48 GB L40S = sub-GPU; HAMi caps VRAM
   ```
   Verify HAMi capped it: `kubectl exec <pod> -c kserve-container -- nvidia-smi --query-gpu=memory.total --format=csv`
   should show **24576 MiB**, not the physical size. `HAMI-core` memory-limiter logs on exit.

2. **Weights persist on an NFS PVC** (`nfs-models` SC — see NFS gotcha #4). Apply the SC + PVC
   first; the init container downloads from HF once (gated repos need `HF_TOKEN`; move to a
   Secret for non-test), then every restart/cold-start reuses the weights.

```bash
kubectl apply -f models/command-r-7b/pvc.yaml    # nfs-models SC auto-deployed (30-nfs.yaml)
kubectl apply -f models/command-r-7b/inferenceservice.yaml
kubectl get isvc command-r-7b -n models -w        # wait for READY=True (first run pulls ~9GB vLLM image)
```

**Scaling model:** cards carry a `scaling` block (`scale_to_zero`, `cold_start_estimate`,
`idle_retention`). Most models run `minReplicas: 0` (scale-to-zero, idle retention); a few
stay `minReplicas: 1` (always-warm). When a request hits a scaled-to-zero model, the gateway
detects 0 ready replicas, runs a capacity check, and returns a fast
`503 {code: model_scaled_to_zero}` "retry in <estimate>" (or `503 insufficient_capacity`)
instead of hanging into a 504.

### Response telemetry — `resources` block

Every non-streaming chat / embeddings / messages response (and the final Anthropic
`message_delta` for streams) carries a `resources` block next to token `usage`:

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
- **Not yet:** live GPU **utilization %**, instantaneous VRAM in use, GPU index/UUID, node name.
  Those need a metrics source (DCGM exporter or the HAMi metrics endpoint); wire that in to
  populate `gpu_util_pct` / `vram_used_mib` later.

## 5. Tyk wiring (auto-deployed)

Tyk is fully configured by the WW-overlay manifests — no manual steps on a fresh cluster:

| Manifest | What it does |
|---|---|
| `50-tyk-redis.yaml` | Installs Redis (Bitnami) |
| `42-traefik-loadbalancer.yaml` | `rke2-traefik-public` LoadBalancer → MetalLB assigns the public VIP (TLS edge) |
| `51-tyk.yaml` | Installs Tyk OSS; bakes in `TYK_GW_APPPATH`, `ENABLEHASHEDKEYSLISTING`, JSVM (`TYK_GW_ENABLEJSVM`), `MIDDLEWAREPATH`, and the api-defs + middleware volume mounts; 600 s proxy timeouts (long reasoning gens) |
| `52-tyk-loadbalancer.yaml` | Tyk Service — **ClusterIP** (legacy name kept for scripts; the VIP belongs to Traefik) |
| `53-tyk-api-definitions.yaml` | ConfigMap with the API definitions (`model-gateway.json` token auth, proxies to `model-gateway.models.svc:80`, custom_middleware pre/post) |
| `54-tyk-middleware.yaml` | ConfigMap with JSVM middleware: `normalizeAuth` (catch-all key acceptance) + `injectIdentity` (X-Aleph-* from alias/tags) |

API definition: `gateway/tyk/model-gateway-api.json` — `use_keyless:false`, `use_standard_auth:true`,
target `http://model-gateway.models.svc.cluster.local:80`. The committed source
is inlined into `53-tyk-api-definitions.yaml`.

Verify Tyk loaded the API definition:
```bash
kubectl logs -n tyk deploy/gateway-tyk-oss-tyk-gateway | grep -i "Detected\|model-gateway"
# Expect: "Loading API Specification from /opt/tyk-gateway/apps/model-gateway.json"
#         "Detected 1 APIs" and "Checking security policy: Token"
```

---

## Day-2 operations

### Key management (control plane — `tyk-admin.sh`)

Run on any control-plane node — `tyk-admin.sh` is on PATH (baked at
`/usr/local/bin`; source: `ww-overlays/overlays/control-plane/usr/local/bin/tyk-admin.sh`).
It reads the APISecret from the in-cluster Secret
(`secrets-tyk-oss-tyk-gateway` / `APISecret`), auto-discovers the Tyk endpoint
(LB VIP, else ClusterIP), and writes an audit log (`/var/log/aleph/tyk-admin.log`).

```bash
# Mint a key (prints the key string). identity = service name OR cluster username.
KEY=$(tyk-admin.sh add-user openwebui shared-pool service)

tyk-admin.sh validate-key openwebui "$KEY"   # true/false (exit 0/1)
tyk-admin.sh update-user openwebui           # rotate: new key + revoke old
tyk-admin.sh invalidate-key "$KEY"
tyk-admin.sh list-user openwebui
tyk-admin.sh invalidate-user openwebui
```

Full key/identity documentation: [`../TYK-USERS.md`](../TYK-USERS.md).

**Identity model.** Tyk OSS has no "user" object. Identity is stored on the key as
the **alias** (= identity) and **tags** (`account:<x>`, `type:<service|user>`).
We deliberately do NOT use `meta_data` — Tyk OSS wipes it on the first request,
while alias + tags persist. The `injectIdentity` JSVM post-hook reads alias/tags
and stamps `X-Aleph-Identity`/`-Account`/`-Identity-Type` on the upstream request;
the gateway logs these on every request (see Usage accounting below).

**Catch-all auth.** Clients may send the key as `Authorization: Bearer`,
`x-api-key`, `api-key`, `x-goog-api-key`, or `?api_key=` — the `normalizeAuth`
pre-hook normalizes any of them to Bearer before auth.

<details><summary>Raw Tyk REST API (under the hood)</summary>

The Tyk admin API is authenticated with `x-tyk-authorization: <APISecret>`. Keys
live in Redis (hash-only — back that datastore up; keys cannot be re-derived).
Keys only take effect when the API is protected (`use_keyless:false`,
`use_standard_auth:true`).

```bash
# Run from a control-plane node (keep the admin API off the public edge):
TYK=http://<tyk-svc-clusterip>:8080
SECRET=$(kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk -o jsonpath='{.data.APISecret}' | base64 -d)

curl -s -X POST $TYK/tyk/keys/create -H "x-tyk-authorization: $SECRET" -H "Content-Type: application/json" -d '{
  "alias": "openwebui",
  "tags": ["aleph", "account:shared-pool", "type:service"],
  "access_rights": {"model-gateway": {"api_id": "model-gateway", "api_name": "model-gateway", "versions": ["Default"]}}
}'
# -> {"key":"<TYK_KEY>","key_hash":"...","status":"ok","action":"added"}
```

| Action | Call (against `$TYK/tyk/...`) |
|---|---|
| Issue key for a user | `POST /tyk/keys/create` (body above; identity = `alias` + `type:<user\|service>` tag — NOT `meta_data`, which Tyk OSS wipes) |
| Deterministic key id | `POST /tyk/keys/<your-id>` (same body) — you choose the token, e.g. derive from uid |
| List all keys | `GET /tyk/keys` → `{"keys":[<hash>,...]}` (hashes, not raw tokens) |
| Inspect by raw key | `GET /tyk/keys/<key>` (shows `alias`, `meta_data`, `access_rights`) |
| Inspect by hash | `GET /tyk/keys/<hash>?hashed=true` (use the hashes from the list) |
| Update a key | `PUT /tyk/keys/<key>` (re-send full body to change quota/rate/meta) |
| Revoke by raw key | `DELETE /tyk/keys/<key>` |
| Revoke by hash | `DELETE /tyk/keys/<hash>?hashed=true` (effective after the ~10s session cache) |

</details>

Primary tool: `tyk-admin.sh` (above). The `gateway/tyk/tyk-keys.sh` helper still
works for quick list/inspect/test but stores identity in `meta_data.username`
(wiped on first request) — prefer `tyk-admin.sh`.

**List / revoke by identity:** Tyk OSS has **no identity index** — `GET /tyk/keys`
only returns hashes. So `list-user` / `invalidate-user` *scan*: list hashes →
`GET /tyk/keys/<hash>?hashed=true` → filter on `alias` → `DELETE` each match. O(n)
over all keys — fine for modest counts.

Lifecycle: no key → `401`; valid key → `200`; bad key → `403`. Tyk keeps
an in-memory **session cache (~10s)**, so a revoked key may keep working briefly —
expected, not a bug.

> `TYK_GW_ENABLEHASHEDKEYSLISTING`, `TYK_GW_APPPATH`, `TYK_GW_ENABLEJSVM`, and
> `TYK_GW_MIDDLEWAREPATH` are baked into `51-tyk.yaml` via `extraEnvs`.
>
> Per-user **rate limit / quota** go in `access_rights.model-gateway.limit`
> (`rate`, `per`, `quota_max`, `quota_renewal_rate`).

### Usage accounting / fairshare

The gateway writes one JSON line per request to the usage-log PVC
(`model-gateway-usage-logs`, RWX NFS — survives pod replacement and re-images) for
fairshare/billing — full schema in [`../LOGGING.md`](../LOGGING.md):

```bash
kubectl exec -n models deploy/model-gateway -c gateway -- tail -f /var/log/aleph/usage.log
```

Each record has `identity`/`account`/`identity_type`, `model`, `api`, `status`,
`latency_ms`, `cold_start`, `tokens` (prompt/completion/total + `detail` = verbatim
vLLM usage with reasoning/cached breakdown), `context_window`,
`max_completion_tokens`, `resources` (gpus, vram_mib, cpu_cores, system_ram_mib,
`gpu_product`, `node`), `derived.gpu_seconds`, and a key `key_fp` fingerprint.
Per-model rollups are on `/metrics`. `gpu_product`/`node` come from the
`node-labeler` DaemonSet (`11-node-labeler.yaml`) labels (`aleph.gpu/product` etc).

### Verify

```bash
# Mint the smoke key on a CP node (admin API is in-cluster only):
K=$(ssh <cp-node> "tyk-admin.sh add-user smoketest" | tail -1)

U=https://<public-hostname>    # public TLS endpoint

curl -s -o /dev/null -w '%{http_code}\n' $U/v1/models                       # 401 (no key)
curl -s $U/v1/models -H "Authorization: Bearer $K"                          # 200 list
curl -s $U/v1/chat/completions -H "Authorization: Bearer $K" -H "Content-Type: application/json" \
  -d '{"model":"command-r-7b","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'   # OpenAI
curl -s $U/v1/messages -H "Authorization: Bearer $K" -H "Content-Type: application/json" \
  -d '{"model":"command-r-7b","max_tokens":20,"messages":[{"role":"user","content":"hi"}]}'   # Anthropic
```

OpenAI SDK: `base_url="https://<public-hostname>/v1"`, `api_key=<tyk key>`.
Anthropic SDK: `base_url="https://<public-hostname>"` (it appends `/v1/messages`), `api_key=<tyk key>`.

### Gotchas we hit (read before redeploying)

1. **`ctr` import socket** — must use `--address /run/k3s/containerd/containerd.sock`; the default
   talks to the host's Docker containerd and the pod gets `ErrImageNeverPull`.
2. **Tyk APPPATH** — Helm default `TYK_GW_APPPATH` points at an empty scratch emptyDir, so Tyk
   loads **0 APIs**. Point it at the API-defs ConfigMap mount (`/opt/tyk-gateway/apps`).
3. **Tyk key listing off by default** — set `TYK_GW_ENABLEHASHEDKEYSLISTING=true` or `GET /tyk/keys`
   errors. List returns **hashes only**; raw tokens aren't recoverable (store at create time).
4. **NFS large-write EIO (SOLVED)** — the default SC mounts NFSv4.2 with `wsize/rsize=1Mi`; some
   backends (e.g. OneFS/Isilon) return `Errno 5 Input/output error` on COMMIT for >128Ki write RPCs over
   NFSv4.1/4.2, so multi-GB safetensors failed at `close()` (small files OK).
   **Fix:** the `nfs-models` SC (auto-deploy `ww-overlays/.../30-nfs.yaml`) sets
   `mountOptions: nfsvers=4.2,wsize=131072,rsize=131072` → ~700 MB/s, verified. Model PVCs use this
   SC so weights persist and **scale-from-zero cold starts skip the re-download** (~90s vs ~3min).
   (NFSv3 and v4.0 also work at default wsize; the 1Mi RPC on v4.1+ is the trigger.)
   **GOTCHA (why it "didn't take" on deploy):** the nfs-subdir chart renders the SC's
   `mountOptions` from `.Values.nfs.mountOptions`, NOT `.Values.storageClass.mountOptions`. The
   overlay originally put them under `storageClass:`, which the chart silently ignores → SC came up
   with empty mountOptions, PVs mounted at 1Mi, and the SC had to be manually deleted+recreated
   (mountOptions is immutable, so a helm upgrade can't patch it). Fixed by moving the list under
   `nfs:` in `30-nfs.yaml`. To verify after a deploy:
   `kubectl get sc nfs-models -o jsonpath='{.mountOptions}'` (must be non-empty).
5. **vLLM image is ~9 GB** — first model start on a fresh GPU node is slow (image pull). Subsequent
   starts are fast.
6. **Bearer prefix** — Tyk strips `Bearer `, so OpenAI/Anthropic SDKs work; raw key also accepted.
7. **Public access** — MetalLB L2 VIP → `rke2-traefik-public` LoadBalancer (TLS, Let's Encrypt)
   → Tyk. Never expose the Tyk admin API (`/tyk/*`) through the edge.
8. **Fresh node has no container builder** — no docker/podman. Install one (`apt-get install -y
   podman`). podman tags images `localhost/...`; retag to `docker.io/library/...` so the bare
   image name in the deployment resolves.
9. **Fresh Tyk has no API-defs mount** — the `tyk-oss` Helm install only mounts an empty scratch
   emptyDir. You must create **and mount** the `tyk-api-definitions` ConfigMap, not just set
   APPPATH.
10. **`gpu=on` label** — HAMi's device-plugin won't run and `nvidia.com/gpu` stays absent without
    it. On this platform `09-gpu-autolabel.yaml` applies it automatically at boot; on a hand-built
    cluster: `kubectl label node <GPU_NODE> gpu=on`.

### Teardown (to redo cleanly)

```bash
# Remove a specific model:
kubectl delete isvc <model> -n models
kubectl delete cm <model>-details -n models

# Remove all model cards:
kubectl delete cm -n models -l model-details=true

# Tyk keys persist in Redis; delete via the admin API if needed (tyk-keys.sh revoke-user <user>).

# The gateway Deployment, RBAC, Service, Tyk LB svc, and api-def ConfigMap are managed by
# the WW-overlay manifests — they are re-applied automatically on the next RKE2 reconcile.
# To force-remove them manually (e.g. to test a full rebuild):
kubectl delete -f ww-overlays/overlays/control-plane/etc/rancher/manifests/63-model-gateway.yaml
kubectl delete -f ww-overlays/overlays/control-plane/etc/rancher/manifests/52-tyk-loadbalancer.yaml
kubectl delete -f ww-overlays/overlays/control-plane/etc/rancher/manifests/53-tyk-api-definitions.yaml
```

---

## Reference

### GPU format conversion cheatsheet (GPU Operator → HAMi)

| | GPU Operator (legacy) | HAMi (this platform) |
|---|---|---|
| Node select | `nvidia.com/gpu.product: NVIDIA-L40S` | label `gpu=on` |
| Whole GPU (>40 GB/card, TP≥2, large TP1) | `nvidia.com/gpu: 4` | `nvidia.com/gpu: "4"` + **NO `gpumem`** (HAMi binds tenant-free cards, full VRAM) |
| Shared slice (<40 GB) | n/a | `nvidia.com/gpu: "1"` + `nvidia.com/gpumem: "10240"` (MiB) |
| Slicing | operator time-slice config | HAMi `deviceSplitCount: 10` (10 vGPU per physical card) |
| TP≥2 extra | — | always `--disable-custom-all-reduce` (L40S PCIe, no P2P) + `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1` |

> The old "`gpumem: 46068` for whole GPUs" workaround (HAMi#1781 era) is **obsolete** —
> whole-device requests without `gpumem` schedule cleanly since the NCCL fix.

### Migrating models from a legacy cluster

Reuse, don't reinvent. Per model:

1. **Trim + extend** the existing `details.yaml`: drop K8s-duplicated fields (`server_config`,
   `deployment.gpu*`, `container_image`, `node`) and runtime-derivable ones, move catalog text
   (`description`, `license`, `tags`, `input_map`/`output_map`) into an optional `catalog` block,
   then add the behavior sections (`param_translation`, `defaults`, `behavior`). Bump
   `schema_version`. See the card templates ([`models/DETAILS-TEMPLATE-LLM.md`](../models/DETAILS-TEMPLATE-LLM.md)).
2. **Convert ISVC GPU format:** `nvidia.com/gpu.product` selector → `gpu: "on"` label +
   `nvidia.com/gpu` + `nvidia.com/gpumem` (cheatsheet above).
3. `kubectl apply` ISVC + card → gateway auto-discovers.
4. Verify routing + response.

**Order:** CPU models → single-GPU → multi-GPU → science models. Card migration is
bulk-scriptable (legacy cards often share a v1 schema; the behavior sections template per `type`
and per thinking `mode`, hand-tuned for reasoning models).

### Build phases (for context)

- **Gateway core:** ✅ done. Card-driven gateway, behind Traefik/Tyk, OpenAI + Anthropic
  endpoints, `resources` telemetry, proven against the model fleet.
- **Auth + key management:** ✅ done. Tyk key per user (`alias` = cluster username); per-user
  keys are auto-minted by the login-node PAM hook (`aleph-tyk-key` → CP `tyk-admin.sh`) →
  `~/.aleph_tyk.env` on every SSH login. Manual minting for services/admins via `tyk-admin.sh`.
- **Usage logging:** ✅ done + durable. Gateway emits one JSON log line per request on the RWX
  PVC (survives re-images); Tyk analytics in Redis. GPU-time computed in reporting;
  `/metrics` exposed for whenever Prometheus gets a home.
- **External access:** ✅ done. MetalLB VIP → Traefik → Tyk → model-gateway; real Let's
  Encrypt TLS via cert-manager (HTTP-01), auto-renewing.
- **Model migration:** largely complete; remaining work is per-model card v2 backfill
  (science input/output schemas).
