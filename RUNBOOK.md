# Redeploy Runbook — Model Gateway + HAMi model + Tyk

How we stood up the card-driven model gateway, a sub-GPU model on HAMi, and Tyk API-key
auth on cluster 230. This is a **manual, step-by-step** guide so it can be reproduced on a
**different cluster** — substitute the per-cluster values in the table below.

> Companion docs: `GATEWAY-ARCHITECTURE.md` (design), `CLUSTER-230-PLAN.md` (detailed notes +
> gotchas). The exact command sequence we ran lives in `gateway/remote-deploy.sh`.

---

## 0. Per-cluster values to substitute

Find these on the target cluster first; everything below references them.

| Placeholder | On 230 | How to find it |
|---|---|---|
| `HEAD_IP` | `172.26.92.230` | control-plane node IP you'll expose the NodePort on |
| `GPU_NODE` | `rack15-03` | `kubectl get nodes -l gpu=on` |
| GPU node label | `gpu=on` | label HAMi device-plugin keys on (`kubectl get node <n> --show-labels`) |
| CP node label | `node-role.kubernetes.io/control-plane=true` | `kubectl get node <cp> -o jsonpath='{.metadata.labels}'` |
| `TYK_DEPLOY` | `gateway-tyk-oss-tyk-gateway` (ns `tyk`) | `kubectl get deploy -n tyk` |
| `TYK_SECRET` (APISecret) | _see `.env` (`TYK_SECRET`)_ | `kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk -o jsonpath='{.data.APISecret}' \| base64 -d` |
| Tyk APPPATH mount | `/opt/tyk-gateway/apps` | where the `tyk-api-definitions` CM is mounted in the Tyk pod |
| StorageClass | `nfs-client` | `kubectl get sc` (⚠️ see NFS gotcha) |
| RKE2 containerd sock | `/run/k3s/containerd/containerd.sock` | RKE2 default |

## Full rebuild order (new RKE2 cluster)

The RKE2 cluster **ships with HAMi, Rancher, NFS provisioner, and cert-manager built in**
(plus NVIDIA drivers on the GPU node images). So a rebuild is just:

| Step | What | Where |
|---|---|---|
| A | **Label GPU nodes** `gpu=on` (the one thing the build doesn't do) | `kubectl label node <GPU_NODE> gpu=on` |
| B | Install **Istio + Knative + KServe + Profiles** | `install-kubeflow/01-install.sh` then `02-post-install.sh` (run on the head node) |
| C | Install **Tyk OSS + Redis** (Helm) | `install-kubeflow/04-install-tyk-gateway.sh` *(see note)* |
| D | Deploy **our gateway + model + Tyk wiring** | this runbook, §1–§5 below |

> **Note on step C / Tyk:** `04-install-tyk-gateway.sh` does the Helm install of Tyk + Redis,
> but its API-definition section wires the **old** per-ISVC keyless routes (`/serving/<isvc>/`).
> Our current design routes everything through the **model-gateway** with **token auth**, so
> **§5 below supersedes** that part — run 04 for the Helm install, then apply §5 (single
> `model-gateway` API def + the two env overrides). You can ignore 04's per-ISVC routes.

## Prerequisites — verify the built-ins are healthy

```bash
kubectl label node <GPU_NODE> gpu=on                                                # step A
kubectl get nodes -l gpu=on                                                          # GPU node shows up
kubectl get node <GPU_NODE> -o jsonpath='{.status.allocatable}' | tr ',' '\n' | grep nvidia  # nvidia.com/gpu: N
kubectl get pods -n kube-system | grep -i hami                                       # hami-scheduler + device-plugin
kubectl get sc                                                                       # nfs-client (default)
kubectl get pods -n cert-manager                                                     # cert-manager up
kubectl get deploy -n tyk                                                            # after step C
```

---

## 1. Gateway image (Docker Hub)

CI publishes the gateway to **`rkhoja/aleph`** on Docker Hub (workflow:
`.github/workflows/deploy-gateway.yml`). Tags: moving `latest` and immutable
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

Build on the control-plane host, then import into **RKE2's** containerd. Source: `gateway/`.
Requires docker or podman on the CP node. Set `imagePullPolicy: Never` and a local tag
like `model-gateway:<tag>` only for this path.

```bash
cd $DIR/gateway
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
watches them — no restart needed to add a model.

```bash
kubectl apply -f gateway/cards/                       # e.g. bge-small
kubectl apply -f models/command-r-7b/details.yaml     # the GPU model's card
```

Card schema = `GATEWAY-ARCHITECTURE.md`. Minimal core: `id`, `type`, `endpoints.primary`,
`routing`, `limits`, `behavior`, `param_translation.thinking`, `defaults`. Everything else
(`catalog`) is ignored by the gateway.

## 4. The GPU model on HAMi (`command-r-7b`)

Ported from the POC (232). Two changes vs a normal GPU-operator manifest, both in
`models/command-r-7b/inferenceservice.yaml`:

1. **HAMi scheduling/limits** — instead of `nodeSelector nvidia.com/gpu.product=...`:
   ```yaml
   nodeSelector: { gpu: "on" }          # HAMi node label
   resources:
     limits:
       nvidia.com/gpu: "1"              # 1 vGPU slice
       nvidia.com/gpumem: "24576"       # 24 GB of a 48 GB L40S = sub-GPU; HAMi caps VRAM
   ```
   Verify HAMi capped it: `kubectl exec <pod> -c kserve-container -- nvidia-smi --query-gpu=memory.total --format=csv`
   should show **24576 MiB**, not the physical size.

2. **Weights persist on an NFS PVC** (`nfs-models` SC — see NFS gotcha #4). Apply the SC + PVC
   first; the init container downloads from HF once (gated Cohere repo → needs `HF_TOKEN`; move to a
   Secret for non-test), then every restart/cold-start reuses the weights.

```bash
kubectl apply -f storage/nfs-models-storageclass.yaml      # once per cluster
kubectl apply -f models/command-r-7b/pvc.yaml
kubectl apply -f models/command-r-7b/inferenceservice.yaml
kubectl get isvc command-r-7b -n models -w        # wait for READY=True (first run pulls 9GB vLLM image)
```

   **Scaling model**: cards carry a `scaling` block (`scale_to_zero`, `cold_start_estimate`). Most
   models run `minReplicas: 0` (scale-to-zero, 15m idle retention); a few stay `minReplicas: 1`
   (always-warm). The gateway detects 0 ready replicas, fires an async Knative wake-up, and returns
   a fast `503 {code: model_scaled_to_zero}` "retry in <estimate>" instead of hanging into a 504.

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

> All of 5b/5c are patches on a Helm-managed Deployment — **fold them into Helm values**
> (`tyk-gateway.gateway.extraEnvs` + an `extraVolumes`/`extraVolumeMounts` for the ConfigMap)
> on a real cluster so chart upgrades don't revert them.

`gateway/tyk/model-gateway-api.json` uses `use_keyless:false` + `use_standard_auth:true`
(token auth), `listen_path:/`, target `http://model-gateway.models.svc.cluster.local:80`.

> Both env overrides are patches on a Helm-managed Deployment — **fold them into the Helm values**
> (`tyk-gateway.gateway.extraEnvs`) on a real cluster so chart upgrades don't revert them.

## 6. Verify

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

Responses carry token `usage` **and** a `resources` block (gpus/vram_mib/cpu_cores/system_ram_mib/latency_ms).

## 7. Key management (day-2)

Admin API at `http://<HEAD_IP>:30808/tyk/...` with header `x-tyk-authorization: <TYK_SECRET>`.
Keys store identity in `alias` + `meta_data` (e.g. `username`, `uid`). Helper:

```bash
gateway/tyk/tyk-keys.sh create <user> [uid]   # prints key (store it — list only shows hashes)
gateway/tyk/tyk-keys.sh list
gateway/tyk/tyk-keys.sh find <user>           # scan keys by meta_data.username
gateway/tyk/tyk-keys.sh revoke-user <user>    # revoke all of a user's keys
gateway/tyk/tyk-keys.sh test <key>
```
(set `TYK_URL` / `TYK_SECRET` env if not on 230). Revokes apply after Tyk's ~10s session cache.

---

## Gotchas we hit (read before redeploying)

1. **`ctr` import socket** — must use `--address /run/k3s/containerd/containerd.sock`; the default
   talks to the host's Docker containerd and the pod gets `ErrImageNeverPull`.
2. **Tyk APPPATH** — Helm default `TYK_GW_APPPATH` points at an empty scratch emptyDir, so Tyk
   loads **0 APIs**. Point it at the API-defs ConfigMap mount (`/opt/tyk-gateway/apps`).
3. **Tyk key listing off by default** — set `TYK_GW_ENABLEHASHEDKEYSLISTING=true` or `GET /tyk/keys`
   errors. List returns **hashes only**; raw tokens aren't recoverable (store at create time).
4. **NFS large-write EIO (SOLVED)** — the default `nfs-client` SC mounts NFSv4.2 with
   `wsize/rsize=1Mi`; the OneFS/Isilon backend returns `Errno 5 Input/output error` on COMMIT for
   >128Ki write RPCs over NFSv4.1/4.2, so multi-GB safetensors failed at `close()` (small files OK).
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
   APPPATH. (Verified during a full rebuild on 2026-06-04.)
10. **`gpu=on` label** — the cluster build does not label GPU nodes. Without it HAMi's device-plugin
    won't run and `nvidia.com/gpu` stays absent. `kubectl label node <GPU_NODE> gpu=on`.

## Teardown (to redo cleanly)

```bash
kubectl delete -f models/command-r-7b/inferenceservice.yaml
kubectl delete cm command-r-7b-details -n models
kubectl delete -f gateway/k8s/deployment.yaml -f gateway/k8s/service.yaml -f gateway/k8s/rbac.yaml
kubectl delete cm -n models -l model-details=true
kubectl delete -f gateway/tyk/nodeport.yaml
kubectl delete cm tyk-api-definitions -n tyk     # then restart Tyk
# Tyk keys persist in Redis; delete via the admin API if needed.
```
