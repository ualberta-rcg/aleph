# Aleph — RKE2 / Warewulf / HAMi Inference Platform

This repo (`ualberta-rcg/aleph`) holds the manifests, gateway, install scripts, and
docs for an RKE2 Kubernetes cluster running HAMi (HAMi) vGPU scheduling and a
KServe/Knative + Tyk model-inference platform.

> **Secrets live in `.env` (gitignored), never in committed files.** See
> [Secrets & `.env`](#secrets--env) below. Copy `.env.example` → `.env` and fill it in.

## Repo Layout

| Path | What |
|---|---|
| `gateway/` | FastAPI inference gateway (OpenAI + Anthropic compatible), Dockerfile, k8s manifests, Tyk config |
| `models/` | Per-model KServe `InferenceService` + `PVC` + `details.yaml` card + `test.py` battery (template: `models/test.template.py`) |
| `ww-overlays/` | Warewulf overlay + RKE2 auto-deploy manifests (baked into node image); site-value tokens + post-deploy steps |
| `deploy-aleph/` | Legacy reference (superseded by `ww-overlays/`). Only `03-deploy-test-model.sh` → now `ww-overlays/post-deploy/verify-test-model.sh` |
| `gateway/test.py` | Model-agnostic gateway checks (catalog, health, guardrails, auth); `FLEET=1` warms + probes every model |
| `scripts/` | Ops helpers — `test-model.sh` (apply / recreate / up / status / cycle a model) |
| `docs/` + `CHANGELOG.md` | Design + ops docs (`RUNBOOK`, `GATEWAY-DESIGN`, `GATEWAY-ARCHITECTURE`, `CHANGELOG`) |

## Cluster Overview — Aleph POC Cluster

HA RKE2 cluster with 3 control plane nodes and 2 GPU workers. Becoming the production platform.

## Access

All commands run from Vulcan login node (`rahimk`). SSH to kube nodes as root:

```bash
# Control plane (3× HA VMs, no GPUs)
sudo ssh root@172.26.92.43  # aleph1 (primary)
sudo ssh root@172.26.92.44  # aleph2
sudo ssh root@172.26.92.45  # aleph3

# Workers (GPU nodes)
sudo ssh root@172.26.93.227 # rack15-03
sudo ssh root@172.26.93.80  # rack05-16
```

### kubectl on nodes

Once SSH'd into any control plane node, `kubectl` works without restriction — no PATH or KUBECONFIG setup needed inside the node shell. From the Vulcan login node, you still need:

```bash
sudo ssh root@172.26.92.43 "export PATH=\$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl get nodes"
```

## Public Endpoint

MetalLB L2 VIP at `129.128.190.55` on interface `enp6s19`. Tyk API gateway exposed as LoadBalancer on port 80 (the primary endpoint). NodePort `30808` is the LB's backing port (also usable internally). All model API traffic goes through Tyk (auth) → model-gateway (FastAPI) → KServe pods.

## Warewulf + Stateless Nodes

Nodes are provisioned via **Warewulf** — they are stateless and can be reprovisioned/replaced. RKE2 auto-deploy manifests go in `/var/lib/rancher/rke2/server/manifests/` on control plane nodes. GPU nodes can be scaled by adding more Warewulf-provisioned workers.

## GPU Setup (No GPU Operator)

This cluster does **NOT** use the NVIDIA GPU Operator. Instead:
- **NVIDIA drivers** are installed directly on GPU node OS images (Warewulf overlay)
- **HAMi** provides the device plugin + vGPU scheduler (replaces both nvidia-device-plugin and GPU Operator)
- **nvidia-container-cli** is on the host for container GPU injection
- GPUs: 8x NVIDIA L40S (48 GB each) — 4 on rack15-03 + 4 on rack05-16

### HAMi Configuration

- HAMi device plugin DaemonSet requires `gpu=on` node label
- Scheduler uses `binpack` GPU policy + `spread` node policy
- Each L40S is split into 10 vGPU slices (deviceSplitCount: 10)
- Total allocatable: `nvidia.com/gpu: 80` (8 physical × 10 split)
- Request VRAM: `nvidia.com/gpumem: "10240"` (MiB)

## Cluster

| Node | IP | Role | OS | GPUs |
|---|---|---|---|---|
| aleph1 | 172.26.92.43 | control-plane, etcd (VM) | Ubuntu 24.04 | none |
| aleph2 | 172.26.92.44 | control-plane, etcd (VM) | Ubuntu 24.04 | none |
| aleph3 | 172.26.92.45 | control-plane, etcd (VM) | Ubuntu 24.04 | none |
| rack15-03 | 172.26.93.227 | worker | Ubuntu 24.04 | 4× L40S 48GB |
| rack05-16 | 172.26.93.80 | worker | Ubuntu 24.04 | 4× L40S 48GB |

- **Kubernetes**: v1.36.1+rke2r2
- **CNI**: Canal + Multus
- **Ingress**: Traefik (RKE2 bundled)
- **Storage**: NFS provisioner (`nfs-models` StorageClass, default)
- **Public VIP**: 129.128.190.55 (MetalLB L2)

## Workloads / Namespaces

| Namespace | Purpose |
|---|---|
| kube-system | Core + HAMI scheduler/device-plugin, RKE2 components |
| models | Model ISVCs + model-gateway deployment |
| tyk | Tyk OSS API gateway + Redis (auth layer) |
| istio-system | Istio service mesh (serving stack) |
| knative-serving | Knative Serving (scale-to-zero, revisions) |
| kubeflow | KServe controller |
| kubeflow-system | Kubeflow system components |
| kuberay | KubeRay operator (Ray clusters on K8s) |
| cert-manager | TLS cert automation |
| nfs-provisioner | NFS dynamic PV provisioning |
| metallb-system | MetalLB L2 load balancer |

### Key pods (kube-system)
- `hami-scheduler` — HAMI vGPU scheduler (2/2 containers)
- `hami-device-plugin-*` — on each GPU node (requires `gpu=on` label)

## Gateway Stack

```
Internet → MetalLB VIP (129.128.190.55:80) → Tyk OSS (auth, rate-limit)
  → model-gateway (FastAPI :8080, ClusterIP in models ns)
    → KServe pods via knative-local-gateway
```

- **Gateway image**: `rkhoja/aleph:latest` (CI auto-builds on `main` push touching `gateway/**`, ~4 min)
- **Gateway deploy**: `kubectl rollout restart deploy/model-gateway -n models` — the manifest pins `:latest` + `imagePullPolicy: Always`, so a restart always pulls the newest CI build. (Pin a specific immutable build only if you need to: `kubectl set image deploy/model-gateway -n models gateway=rkhoja/aleph:gateway-<sha>`.)
- **Tyk keys**: `gateway/tyk/tyk-keys.sh` (create/list/inspect/revoke)
- **Gateway update**: `kubectl rollout restart deploy/model-gateway -n models` (CI auto-builds `rkhoja/aleph:latest` on every `gateway/**` push)

## POC Reference Cluster (172.26.92.232)

The first POC cluster at `kubeflow-head-node` (172.26.92.232) runs a full Kubeflow inference platform.
Install docs and working configs are on that node at `/root/kuberflow-working/`.

### POC Key Files
- `/root/kuberflow-working/install-kubeflow/` — install scripts, manifests, configs
- `/root/kuberflow-working/models/` — 63+ InferenceService deployments
- `/root/kuberflow-working/gateway/` — FastAPI unified inference gateway
- `/root/kuberflow-working/CLAUDE.md` — detailed project notes

## Secrets & `.env`

Secrets are **not** committed. The repo root has a gitignored `.env` (real values) and a
committed `.env.example` (template). Required values:

- `HF_TOKEN` — HuggingFace token used by model init/download containers.
- `TYK_SECRET` / `TYK_API_SECRET` — Tyk OSS gateway `APISecret` (admin API).

### HuggingFace token → k8s Secret

Model manifests reference the token via a Secret (`hf-token` in the `models` namespace),
not an inline value. Create/refresh it from `.env` before deploying models:

```bash
set -a; source .env; set +a
kubectl create secret generic hf-token -n models \
  --from-literal=token="$HF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Tyk secret

`gateway/tyk/tyk-keys.sh` reads `TYK_SECRET` / `TYK_API_SECRET` from the environment. Export
from `.env` (e.g. `set -a; source .env; set +a`) before running.

## Changelog-First Commit Process

Every code/config change must be reflected in `CHANGELOG.md` **before** creating a commit.

### Required workflow (before `git commit`)

1. Group related edits into one logical change.
2. Add/update a dated entry in `CHANGELOG.md` (newest-first).
3. Include:
   - what changed,
   - why it changed,
   - deployment/operational impact,
   - validation performed (tests/commands/results).
4. If the change is partial/in-progress, mark it clearly as follow-up required.
5. Stage `CHANGELOG.md` in the same commit as the code/manifests it describes.

### Commit gate

- Do **not** commit if code changed but `CHANGELOG.md` was not updated.
- Small exceptions (typos/comments-only) are allowed, but should be explicitly noted in the commit message.

## Card Templates (v2 Schema — one standard)

`models/DETAILS-TEMPLATE-LLM.md` is the single source of truth for card format. All 3 templates use the **v2 compact schema** tested against the gateway.

**v2 schema structure** (gateway reads only these top-level keys):
`id`, `type`, `endpoints`, `routing`, `limits`, `scaling`, `behavior`, `param_translation`, `defaults`, `custom_params`, `schema_version`, `input_map`, `output_map`, `catalog`

Everything else (`owned_by`, `license`, `tags`, `description`, `deployment`, `server_config`, etc.) goes inside `catalog` — the gateway ignores it but the UI/catalog uses it.

**Do NOT use `compatibility` or `deployment` blocks.** The gateway reads `behavior.*` only.

| Template | Use for |
|---|---|
| **A — vLLM chat LLM** | Chat models (gemma, qwen, deepseek, etc.) + completions-only (progen2) + reasoning (phi-4) |
| **B — Custom science server** | FastAPI science models (diffdock, aurora, esmfold, etc.) — 5 I/O patterns documented |
| **C — Embedding/rerank/audio/classification** | Non-LLM standard-endpoint models (bge, scibert, birdnet, etc.) |

All templates include `input_map`/`output_map` (documentation-only, gateway does not read them).

### Thinking/reasoning
- Use `param_translation.thinking` with `"mode": "budget"` to map effort → `thinking_token_budget`
- Always include `"disabled_effort": "none"` so thinking can be turned off
- `"mode": "none"` for non-reasoning models (default)

### OpenWebUI compat
- `defaults.meta_tasks` with title/tags/followups controls OpenWebUI auto-generation
- `defaults.chat` sets default temperature/max_tokens

### Anthropic endpoint
- Only `type: "chat"` models get Anthropic `/v1/messages` translation (gateway gates on type)
- `type: "completions"` or science types → 400 on Anthropic endpoint

### LLM Model Progress

Phase 1 complete (v2 schema + tested through gateway + input_map/output_map):
1. ✅ tinyllama (14/14)
2. ✅ command-r-7b (16/16)
3. ✅ deepseek-v2-lite-16b (14/14)
4. ✅ openbiollm-70b (14/14)
5. ✅ oceangpt-30b (14/14, tools)
6. ✅ geogalactica (14/14)
7. ✅ astrosage (14/14, no_stream)
8. ✅ progen2 (8/10, completions-only)

Remaining LLMs still on v1 schema — see `models.md` for full list.

## Working Conventions

- This repo is the source of truth; clone is at `/scratch/rahimk/repos/aleph` on the login node.
- Run kubectl commands via SSH to any control plane node (aleph1 preferred)
- For quick one-liners:
  ```bash
  sudo ssh root@172.26.92.43 "export PATH=\$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl get nodes"
  ```
- For multi-command work, SSH in interactively or chain with `&&`

## Scaling Models Up/Down

**Always-up** is the catalog flag `details.scaling.scale_to_zero: false` (not merely
`minReplicas ≥ 1`). Those models run `minReplicas: 1` and stay in `/v1/models`. Scale-to-zero
models have `scale_to_zero: true` and `minReplicas: 0`.

**Never `kubectl patch` an InferenceService** (min/max/`scaleTarget`/args/image or anything else).
A patch creates a new Knative revision that fights the old one for GPUs. Always **delete the
ISVC and re-apply YAML**; **never delete the PVC**. Re-apply `details.yaml` only if the card
should stay listed.

Scale the gateway to 0 before bouncing if users would otherwise wake cold models; bring it back
to 3 only after always-up pods are Ready.

### Restart / bounce an ISVC (keep weights)
```bash
kubectl delete isvc <model> -n models
# do not delete the PVC
kubectl apply -f models/<model>/inferenceservice.yaml
# re-apply the card only if it should stay in the catalog:
kubectl apply -f models/<model>/details.yaml
```

### Park a model (hide from catalog)

**Parked means only this: delete the details ConfigMap from the prod cluster.**
The InferenceService and PVC stay. The card YAML stays in the repo. Un-park later by
re-applying that ConfigMap — nothing else.

```bash
# park (catalog hides it; ISVC/PVC untouched)
kubectl delete cm <model>-details -n models

# un-park (lists it again in /v1/models)
kubectl apply -f models/<model>/details.yaml
```

Do **not** delete the ISVC or PVC just to park. Park is not `stop`.

### `serving.kserve.io/stop` (different from park)

`stop=true` fully stops the InferenceService: no pods, and it will **not** wake on demand.
Knative honors this even when `minReplicas: 1`. The card still lists the model in `/v1/models`
if the ConfigMap is present. Use this when a model must not run, not to hide it from the catalog.

```bash
# stop — no pods, blocks wake-on-demand
kubectl annotate isvc <model> -n models serving.kserve.io/stop=true --overwrite

# clear stop — wake-on-demand again (min 0) or stay always-up (min 1)
kubectl annotate isvc <model> -n models serving.kserve.io/stop- --overwrite
```

Just setting `minReplicas: 0` is not enough to stop a model; without `stop`, the first
request wakes it. Do not `kubectl patch` the ISVC spec to toggle this — if the YAML must
change, delete the ISVC, keep the PVC, re-apply.

### Check readiness
```bash
kubectl get isvc <model> -n models -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
```
