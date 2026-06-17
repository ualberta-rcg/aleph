# Operations Guide — Model Inference Gateway

How to stand up and operate the card-driven model inference gateway: a FastAPI gateway
(card routing + OpenAI/Anthropic translation) fronted by **Tyk** (token auth), serving
models on **HAMi** fractional GPUs via **KServe/Knative**. This is a **manual, step-by-step**
guide so it can be reproduced on **any** equivalent cluster.

> **Cluster-specific values** (IPs, hostnames, the worked-example values for the **230**
> test/POC cluster and the **232** legacy POC it replaced) are **not committed here** — they
> live in the local working directory on the deploy host. The table in §0 uses placeholders;
> fill them in for your cluster. No cluster number appears in this file by design.
>
> Companion docs (this repo): [`GATEWAY-DESIGN.md`](GATEWAY-DESIGN.md) (design rationale),
> [`GATEWAY-ARCHITECTURE.md`](GATEWAY-ARCHITECTURE.md) (card schema + handler map). The exact
> command sequence run live is in `gateway/remote-deploy.sh`.

---

## Architecture at a glance

```
client ──HTTP──> <HEAD_IP>:30808 ──> Tyk (token auth/keys, Redis) ──> model-gateway (cards)
                                                                       │
                                            ┌──────────────────────────┴───────────────────────────┐
                                            ▼ (Knative local gateway, Host: <isvc>-predictor)       ▼ (direct Service / RayService)
                                       KServe ISVC predictors — chat / embed / science        media backends (image gen, TTS)
                                            ▼
                                       HAMi vGPU slices on GPU workers (label gpu=on)
```

- **Gateway** is pinned to control-plane (non-GPU) nodes; it never steals resources from model pods.
- **Two backend planes:** most models are Knative `InferenceService`s (scale-to-zero); a few media
  models run as raw `Deployment`/`RayService` behind the cluster ingress (Plane 2).
- **Cards are the single source of model truth.** The gateway reads them at runtime — adding a
  model = apply an ISVC + a card ConfigMap, **zero gateway changes, zero restart**.

---

## 0. Per-cluster values to substitute

Find these on the target cluster first; every command below references them.

| Placeholder | What it is | How to find it |
|---|---|---|
| `HEAD_IP` | control-plane node IP you'll expose the NodePort on | the CP VM address |
| `GPU_NODE` | a GPU worker hostname | `kubectl get nodes -l gpu=on` |
| GPU node label | label HAMi device-plugin keys on | `gpu=on` (label it if missing — see gotcha #9) |
| CP node label | control-plane selector | `node-role.kubernetes.io/control-plane=true` |
| `TYK_DEPLOY` | Tyk gateway Deployment | `kubectl get deploy -n tyk` (Helm default `gateway-tyk-oss-tyk-gateway`) |
| `TYK_SECRET` | Tyk admin `APISecret` | `kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk -o jsonpath='{.data.APISecret}' \| base64 -d` |
| Tyk APPPATH mount | where the `tyk-api-definitions` CM is mounted | `/opt/tyk-gateway/apps` |
| StorageClass | default SC | `kubectl get sc` (⚠️ see NFS gotcha #4) |
| RKE2 containerd sock | socket `ctr` must talk to | `/run/k3s/containerd/containerd.sock` (RKE2 default) |

> The literal values for the **230** and **232** clusters are in the local working dir, not here.

---

## Prerequisites — verify the built-ins are healthy

An RKE2 cluster built the standard way **ships with HAMi, Rancher, the NFS provisioner, and
cert-manager built in** (plus NVIDIA drivers baked into the GPU node images). So a rebuild is:

| Step | What | Where |
|---|---|---|
| A | **Label GPU nodes** `gpu=on` (the one thing the build doesn't do) | `kubectl label node <GPU_NODE> gpu=on` |
| B | Install **Istio + Knative + KServe + Profiles** | `install-kubeflow/01-install.sh` then `02-post-install.sh` (run on the head node) |
| C | Install **Tyk OSS + Redis** (Helm) | `install-kubeflow/04-install-tyk-gateway.sh` *(see note)* |
| D | Deploy **our gateway + model + Tyk wiring** | §1–§5 below |

> **Note on step C / Tyk:** `04-install-tyk-gateway.sh` does the Helm install of Tyk + Redis,
> but its API-definition section wires the **old** per-ISVC keyless routes (`/serving/<isvc>/`).
> The current design routes everything through the **model-gateway** with **token auth**, so
> **§5 supersedes** that part — run 04 for the Helm install, then apply §5 (single
> `model-gateway` API def + the two env overrides). Ignore 04's per-ISVC routes.

```bash
kubectl label node <GPU_NODE> gpu=on                                                # step A
kubectl get nodes -l gpu=on                                                          # GPU node shows up
kubectl get node <GPU_NODE> -o jsonpath='{.status.allocatable}' | tr ',' '\n' | grep nvidia  # nvidia.com/gpu: N
kubectl get pods -n kube-system | grep -i hami                                       # hami-scheduler + device-plugin
kubectl get sc                                                                       # default SC
kubectl get pods -n cert-manager                                                     # cert-manager up
kubectl get deploy -n tyk                                                            # after step C
```

---

## 1. Gateway image (Docker Hub)

CI publishes the gateway to **`rkhoja/aleph`** on Docker Hub
(workflow: `.github/workflows/deploy-gateway.yml`). Tags: moving `latest` and immutable
`gateway-<shortsha>`.

```bash
# Default: pull rkhoja/aleph:latest (imagePullPolicy: IfNotPresent in deployment.yaml)
kubectl apply -f gateway/k8s/deployment.yaml

# Or pin a CI build for reproducibility:
kubectl set image deploy/model-gateway -n models gateway=rkhoja/aleph:gateway-<sha>
kubectl rollout status deploy/model-gateway -n models
```

From a login node, `./deploy.sh` ships manifests and applies everything (no local build).

<details>
<summary>Appendix: local build + containerd import (dev / air-gapped only)</summary>

Build on the control-plane host, then import into **RKE2's** containerd (not the host's — see
gotcha #1). Requires docker or podman on the CP node. Set `imagePullPolicy: Never` and a local
tag like `model-gateway:<tag>` only for this path.

```bash
cd gateway
podman build -t model-gateway:0.3 .
podman save model-gateway:0.3 -o /tmp/gw.tar
CTR="ctr --address /run/k3s/containerd/containerd.sock -n k8s.io"
$CTR images import /tmp/gw.tar
$CTR images tag localhost/model-gateway:0.3 docker.io/library/model-gateway:0.3
```

</details>

## 2. Gateway RBAC + Service + Deployment

```bash
kubectl create namespace models --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f gateway/k8s/rbac.yaml       # SA + Role: configmaps & inferenceservices get/list/watch
kubectl apply -f gateway/k8s/service.yaml    # ClusterIP :80 -> :8080
kubectl apply -f gateway/k8s/deployment.yaml # image rkhoja/aleph:latest, imagePullPolicy: IfNotPresent
```

Key deployment choices (in `gateway/k8s/deployment.yaml`):
- **Pinned to control-plane / non-GPU nodes:** `nodeSelector node-role.kubernetes.io/control-plane: "true"`
  + nodeAffinity `gpu NotIn [on]`. Keeps it off GPU workers; covers all future CP VMs.
- `image: rkhoja/aleph:latest` from Docker Hub (`imagePullPolicy: IfNotPresent`). Container name is **`gateway`** (matters for `kubectl set image`).
- Istio sidecar via pod label `sidecar.istio.io/inject: "true"`.

The gateway needs `gateway/cards/` applied (next step) before `/readyz` goes green
(readiness requires ≥1 card).

## 3. Model cards (the discovery mechanism)

Cards are ConfigMaps labelled `model-details=true`, containing `details.json`. The gateway
watches them — **no restart needed to add a model.**

```bash
kubectl apply -f gateway/cards/                       # e.g. bge-small
kubectl apply -f models/command-r-7b/details.yaml     # a GPU model's card
```

Card schema = [`GATEWAY-ARCHITECTURE.md`](GATEWAY-ARCHITECTURE.md). Minimal core: `id`, `type`,
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
kubectl apply -f storage/nfs-models-storageclass.yaml      # once per cluster
kubectl apply -f models/command-r-7b/pvc.yaml
kubectl apply -f models/command-r-7b/inferenceservice.yaml
kubectl get isvc command-r-7b -n models -w        # wait for READY=True (first run pulls ~9GB vLLM image)
```

**Scaling model:** cards carry a `scaling` block (`scale_to_zero`, `cold_start_estimate`,
`idle_retention`). Most models run `minReplicas: 0` (scale-to-zero, 15m idle retention); a few
stay `minReplicas: 1` (always-warm). When a request hits a scaled-to-zero model, the gateway
detects 0 ready replicas, fires an async Knative wake-up, and returns a fast
`503 {code: model_scaled_to_zero}` "retry in <estimate>" instead of hanging into a 504.

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

## 5. Tyk wiring

A fresh `tyk-oss` Helm install has **no** API-definitions ConfigMap mounted, and
`TYK_GW_APPPATH` points at an empty scratch emptyDir. So we must (a) create the ConfigMap,
(b) **mount it**, (c) point APPPATH at the mount, (d) enable key listing, (e) NodePort.

```bash
TYK_DEPLOY=gateway-tyk-oss-tyk-gateway              # `kubectl get deploy -n tyk`
TYK_CTR=$(kubectl get deploy $TYK_DEPLOY -n tyk -o jsonpath='{.spec.template.spec.containers[0].name}')

# 5a. API definition -> ConfigMap
kubectl create configmap tyk-api-definitions -n tyk \
  --from-file=model-gateway.json=gateway/tyk/model-gateway-api.json \
  --dry-run=client -o yaml | kubectl apply -f -

# 5b. env overrides: read defs from the mount + allow key listing
kubectl set env deploy/$TYK_DEPLOY -n tyk \
  TYK_GW_APPPATH=/opt/tyk-gateway/apps \
  TYK_GW_ENABLEHASHEDKEYSLISTING=true

# 5c. MOUNT the ConfigMap at the APPPATH (the step the fresh install lacks)
kubectl patch deploy $TYK_DEPLOY -n tyk --type=strategic -p '{"spec":{"template":{"spec":{
  "volumes":[{"name":"api-defs","configMap":{"name":"tyk-api-definitions"}}],
  "containers":[{"name":"'"$TYK_CTR"'","volumeMounts":[{"name":"api-defs","mountPath":"/opt/tyk-gateway/apps"}]}]}}}}'

# 5d. Expose Tyk on the host IP (no LB/public IP)
kubectl apply -f gateway/tyk/nodeport.yaml          # NodePort 30808 -> Tyk :8080

# 5e. Roll (the patch/env changes already trigger a rollout; this ensures it)
kubectl rollout status deploy/$TYK_DEPLOY -n tyk --timeout=120s
# Expect logs: "Loading API Specification ... model-gateway.json" -> "Detected 1 APIs"
#              -> "Checking security policy: Token"
```

> 5b/5c are patches on a Helm-managed Deployment — **fold them into Helm values**
> (`tyk-gateway.gateway.extraEnvs` + an `extraVolumes`/`extraVolumeMounts` for the ConfigMap)
> on a real cluster so chart upgrades don't revert them.

`gateway/tyk/model-gateway-api.json` uses `use_keyless:false` + `use_standard_auth:true`
(token auth), `listen_path:/`, target `http://model-gateway.models.svc.cluster.local:80`.

---

## Day-2 operations

### Key management (Tyk OSS REST API)

The Tyk gateway REST API is authenticated with header `x-tyk-authorization: <APISecret>`
(secret `secrets-tyk-oss-tyk-gateway`, key `APISecret`; live value in `.env` as `TYK_SECRET`).
Keys live in Redis, so they persist and work in file-based mode. Keys only take effect when the
API is **protected** (`use_keyless: false`, `use_standard_auth: true`).

Tyk OSS has no separate "user" object, but **every key carries identity** via `alias` (human
label) and `meta_data` (arbitrary map). Issue one key per user and stamp the username/uid/account
on it; the key string is the bearer token the user puts in their client.

```bash
TYK=http://<HEAD_IP>:30808
SECRET=$(kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk -o jsonpath='{.data.APISecret}' | base64 -d)

# Issue a key bound to a user (Tyk generates the key string):
curl -s -X POST $TYK/tyk/keys/create -H "x-tyk-authorization: $SECRET" -H "Content-Type: application/json" -d '{
  "alias": "rahimk",
  "meta_data": {"username": "rahimk", "uid": "100123", "account": "def-pi", "source": "pam"},
  "tags": ["pam"],
  "access_rights": {"model-gateway": {"api_id": "model-gateway", "api_name": "model-gateway", "versions": ["Default"]}}
}'
# -> {"key":"<TYK_KEY>","key_hash":"...","status":"ok","action":"added"}
```

| Action | Call (against `$TYK/tyk/...`) |
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
→ filter on `meta_data.username` → (for revoke-user) `DELETE` each match. This is O(n) over all
keys — fine for modest counts. For large fleets, keep your own username→key index, or use
deterministic key ids (`POST /tyk/keys/<id-derived-from-username>`) so revoke is a direct `DELETE`.

Verified lifecycle: no key → `401`; valid key → `200`; after `DELETE` → `403`. Tyk keeps an
in-memory **session cache (~10s)**, so a revoked key may keep working for a few seconds —
expected, not a bug.

> **Listing had to be enabled** via `TYK_GW_ENABLEHASHEDKEYSLISTING=true` (§5b). Like the APPPATH
> override, move it into the Helm values so a chart upgrade keeps it.
>
> Per-user **rate limit / quota** go in `access_rights.model-gateway.limit`
> (`rate`, `per`, `quota_max`, `quota_renewal_rate`). To get the username into model logs for
> per-user accounting, add a Tyk header transform injecting `$tyk_meta.username` as an upstream
> header (e.g. `X-User`) — not wired yet.

### Verify

```bash
U=http://<HEAD_IP>:30808
S=<TYK_SECRET>

# make a key
K=$(curl -s -X POST $U/tyk/keys/create -H "x-tyk-authorization: $S" -H "Content-Type: application/json" \
  -d '{"alias":"smoketest","access_rights":{"model-gateway":{"api_id":"model-gateway","api_name":"model-gateway","versions":["Default"]}}}' \
  | sed -n 's/.*"key":"\([^"]*\)".*/\1/p')

curl -s -o /dev/null -w '%{http_code}\n' $U/v1/models                       # 401 (no key)
curl -s $U/v1/models -H "Authorization: Bearer $K"                          # 200 list
curl -s $U/v1/chat/completions -H "Authorization: Bearer $K" -H "Content-Type: application/json" \
  -d '{"model":"command-r-7b","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'   # OpenAI
curl -s $U/v1/messages -H "Authorization: Bearer $K" -H "Content-Type: application/json" \
  -d '{"model":"command-r-7b","max_tokens":20,"messages":[{"role":"user","content":"hi"}]}'   # Anthropic
```

OpenAI SDK: `base_url="http://<HEAD_IP>:30808/v1"`, `api_key=<tyk key>`.
Anthropic SDK: `base_url="http://<HEAD_IP>:30808"` (it appends `/v1/messages`), `api_key=<tyk key>`.

### Gotchas we hit (read before redeploying)

1. **`ctr` import socket** — must use `--address /run/k3s/containerd/containerd.sock`; the default
   talks to the host's Docker containerd and the pod gets `ErrImageNeverPull`.
2. **Tyk APPPATH** — Helm default `TYK_GW_APPPATH` points at an empty scratch emptyDir, so Tyk
   loads **0 APIs**. Point it at the API-defs ConfigMap mount (`/opt/tyk-gateway/apps`).
3. **Tyk key listing off by default** — set `TYK_GW_ENABLEHASHEDKEYSLISTING=true` or `GET /tyk/keys`
   errors. List returns **hashes only**; raw tokens aren't recoverable (store at create time).
4. **NFS large-write EIO (SOLVED)** — the default SC mounts NFSv4.2 with `wsize/rsize=1Mi`; the
   OneFS/Isilon backend returns `Errno 5 Input/output error` on COMMIT for >128Ki write RPCs over
   NFSv4.1/4.2, so multi-GB safetensors failed at `close()` (small files OK).
   **Fix:** dedicated SC `nfs-models` (`storage/nfs-models-storageclass.yaml`) with
   `mountOptions: nfsvers=4.2,wsize=131072,rsize=131072` → ~700 MB/s, verified. Model PVCs use this
   SC so weights persist and **scale-from-zero cold starts skip the re-download** (~90s vs ~3min).
   (NFSv3 and v4.0 also work at default wsize; the 1Mi RPC on v4.1+ is the trigger.)
5. **vLLM image is ~9 GB** — first model start on a fresh GPU node is slow (image pull). Subsequent
   starts are fast.
6. **Bearer prefix** — Tyk strips `Bearer `, so OpenAI/Anthropic SDKs work; raw key also accepted.
7. **No public IP** — use a NodePort on a control-plane node IP. With 3 CP VMs, front with a VIP
   (kube-vip/keepalived) so the endpoint isn't a single point of failure.
8. **Fresh node has no container builder** — no docker/podman. Install one (`apt-get install -y
   podman`). podman tags images `localhost/...`; retag to `docker.io/library/...` so the bare
   image name in the deployment resolves.
9. **Fresh Tyk has no API-defs mount** — the `tyk-oss` Helm install only mounts an empty scratch
   emptyDir. You must create **and mount** the `tyk-api-definitions` ConfigMap (§5c), not just set
   APPPATH.
10. **`gpu=on` label** — the cluster build does not label GPU nodes. Without it HAMi's device-plugin
    won't run and `nvidia.com/gpu` stays absent. `kubectl label node <GPU_NODE> gpu=on`.

### Teardown (to redo cleanly)

```bash
kubectl delete -f models/command-r-7b/inferenceservice.yaml
kubectl delete cm command-r-7b-details -n models
kubectl delete -f gateway/k8s/deployment.yaml -f gateway/k8s/service.yaml -f gateway/k8s/rbac.yaml
kubectl delete cm -n models -l model-details=true
kubectl delete -f gateway/tyk/nodeport.yaml
kubectl delete cm tyk-api-definitions -n tyk     # then restart Tyk
# Tyk keys persist in Redis; delete via the admin API if needed.
```

---

## Reference

### GPU format conversion cheatsheet (GPU Operator → HAMi)

| | GPU Operator (legacy POC) | HAMi (this platform) |
|---|---|---|
| Node select | `nvidia.com/gpu.product: NVIDIA-L40S` | label `gpu=on` |
| Whole GPU | `nvidia.com/gpu: 4` | `nvidia.com/gpu: 4` + `nvidia.com/gpumem: 46068` |
| Shared slice | n/a | `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 10240` |
| Slicing | operator time-slice config | HAMi `deviceSplitCount: 10` |

### Migrating models from a legacy POC cluster

Reuse, don't reinvent. Per model:

1. **Trim + extend** the existing `details.yaml`: drop K8s-duplicated fields (`server_config`,
   `deployment.gpu*`, `container_image`, `node`) and runtime-derivable ones, move catalog text
   (`description`, `license`, `tags`, `input_map`/`output_map`) into an optional `catalog` block,
   then add the behavior sections (`param_translation`, `defaults`, `behavior`). Bump
   `schema_version`. See [`GATEWAY-ARCHITECTURE.md`](GATEWAY-ARCHITECTURE.md) and
   `models/MIGRATION.md`.
2. **Convert ISVC GPU format:** `nvidia.com/gpu.product` selector → `gpu: "on"` label +
   `nvidia.com/gpu` + `nvidia.com/gpumem` (cheatsheet above).
3. `kubectl apply` ISVC + card → gateway auto-discovers.
4. Verify routing + response.

**Order:** CPU models → single-GPU → multi-GPU → science models. Card migration is
bulk-scriptable (the legacy cards share the v1 schema; the behavior sections template per `type`
and per thinking `mode`, hand-tuned for reasoning models).

### Roadmap / phases

- **Phase 1 — Gateway core:** ✅ done. Card-driven gateway built, deployed, behind Tyk,
  OpenAI + Anthropic endpoints, `resources` telemetry, proven against many models.
- **Phase 2 — Auth + key management:** ⚠️ design before code. Tyk key per user (`alias` = LDAP
  username; LDAP used once at key creation, never per-request). Vulcan users provisioned via a
  `/etc/profile.d` Warewulf-overlay script on login → `$HOME/.inference_api_key`. `inference-key`
  CLI (self-service + admin) over the Tyk REST API. ⚠️ review admin-secret distribution
  (Warewulf overlay vs K8s Secret) and public LDAP-bind exposure before building.
- **Phase 3 — Usage logging (no monitoring stack):** partial. Gateway emits one JSON log line per
  request (user/model/tokens/gpu/duration); Tyk analytics already in Redis. GPU-hours computed in
  reporting: `gpu_hours = (ms/3.6e6) × physical_gpu_count × (hami_vram_mb / per_card_vram)`.
  `/metrics` exposed for whenever Prometheus gets a home.
- **Phase 4 — External access:** pending. Traefik IngressRoute → Tyk → `model-gateway`; TLS via
  cert-manager (DNS-01) or manual cert.
- **Phase 5 — Model migration:** largely complete (the bulk of the fleet is migrated and carded);
  remaining work is per-model card v2 backfill (science input/output schema) — see `models/MODEL-STATUS.md`.
