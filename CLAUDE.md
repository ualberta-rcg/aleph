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
| `models/` | Per-model KServe `InferenceService` + `PVC` + `details.yaml` cards (LLMs, embeddings, rerank, TTS, science models) |
| `install-kubeflow/` | Cluster bring-up scripts (RKE2 manifests, Tyk OSS, test model) |
| `storage/` | NFS StorageClass definitions (`nfs-client` default, OneFS-safe mount options) |
| `scratch/` | Test harnesses (`full_test.py` = full OpenAI/Anthropic sweep) |
| `demo/`, `deploy.sh` | Convenience demo + deploy wrapper |
| `*.md` (RUNBOOK, GATEWAY-*, CLUSTER-230-PLAN, CHANGELOG) | Design + ops docs |

## Cluster Overview

RKE2 Kubernetes cluster used for HAMi (HAMi) GPU scheduling and KServe model serving.

## Access

All commands run from Vulcan login node (`rahimk`). SSH to kube nodes as root:

```bash
# Control plane (VM, no GPUs)
sudo ssh root@172.26.92.230    # kubeflow-head-node2

# Worker (GPU node)
sudo ssh root@172.26.93.227    # rack15-03
```

### kubectl on nodes

Once SSH'd into either kube node, `kubectl` works without restriction — no PATH or KUBECONFIG setup needed inside the node shell. From the Vulcan login node, you still need:

```bash
sudo ssh root@172.26.92.230 "export PATH=\$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl get nodes"
```

## Warewulf + Stateless Nodes

Nodes are provisioned via **Warewulf** — they are stateless and can be reprovisioned/replaced. RKE2 auto-deploy manifests go in `/var/lib/rancher/rke2/server/manifests/` on the head node. GPU nodes can be scaled by adding more Warewulf-provisioned workers.

## GPU Setup (No GPU Operator)

This cluster does **NOT** use the NVIDIA GPU Operator. Instead:
- **NVIDIA drivers** are installed directly on GPU node OS images (Warewulf overlay)
- **HAMi** provides the device plugin + vGPU scheduler (replaces both nvidia-device-plugin and GPU Operator)
- **nvidia-container-cli** is on the host for container GPU injection
- GPUs: 4x NVIDIA L40S (48 GB each) on rack15-03

### HAMi Configuration

- HAMi device plugin DaemonSet requires `gpu=on` node label
- Scheduler uses `binpack` GPU policy + `spread` node policy
- Each L40S is split into 10 vGPU slices (deviceSplitCount: 10)
- Total allocatable: `nvidia.com/gpu: 40` (4 physical × 10 split)
- Request VRAM: `nvidia.com/gpumem: "10240"` (MiB)

## Cluster

| Node | IP | Role | OS | GPUs |
|---|---|---|---|---|
| kubeflow-head-node2 | 172.26.92.230 | control-plane, etcd (VM) | Ubuntu 24.04 | none |
| rack15-03 | 172.26.93.227 | worker | Ubuntu 24.04 | 4× L40S 48GB |

- **Kubernetes**: v1.36.1+rke2r2
- **CNI**: Canal + Multus
- **Ingress**: Traefik (RKE2 bundled)
- **Storage**: NFS provisioner (`nfs-client` StorageClass, default)

## Workloads / Namespaces

| Namespace | Purpose |
|---|---|
| kube-system | Core + HAMI scheduler/device-plugin, RKE2 components |
| kuberay | KubeRay operator (Ray clusters on K8s) |
| cert-manager | TLS cert automation |
| nfs-provisioner | NFS dynamic PV provisioning |
| traefik | RKE2 Traefik ingress |

### Key pods (kube-system)
- `hami-scheduler` — HAMI vGPU scheduler (2/2 containers)
- `hami-device-plugin-*` — on each GPU node (requires `gpu=on` label)
- `kuberay-operator` — manages RayCluster CRDs

## POC Reference Cluster (172.26.92.232)

The first POC cluster at `kubeflow-head-node` (172.26.92.232) runs a full Kubeflow inference platform.
Install docs and working configs are on that node at `/root/kuberflow-working/`.

### POC Architecture
```
Internet → Traefik → Istio IngressGateway → oauth2-proxy/Dex (auth)
                                            → KServe InferenceServices (models ns)
                                            → FastAPI Gateway (routing)
```

### POC Kubeflow Install Method
- Kubeflow manifests: `v1.11-branch` from `github.com/kubeflow/manifests`
- Installed via Kubernetes Job (`kubeflow-bootstrap`) that clones and applies kustomize overlays
- KServe CRDs require `--server-side --force-conflicts` (too large for normal apply)
- Components: Istio 1.24, Knative Serving, Dex, oauth2-proxy, KServe, Profiles, Dashboard
- GPU Operator used on POC (NOT used on this cluster — HAMi handles it here)

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

`gateway/tyk/tyk-keys.sh` and `install-kubeflow/04-install-tyk-gateway.sh` read
`TYK_SECRET` / `TYK_API_SECRET` from the environment (no baked-in default). Export them
(e.g. `set -a; source .env; set +a`) before running.

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
- Run kubectl commands via SSH to the control plane node
- For quick one-liners:
  ```bash
  sudo ssh root@172.26.92.230 "export PATH=\$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl get nodes"
  ```
- For multi-command work, SSH in interactively or chain with `&&`

## Scaling Models Up/Down

KServe ISVCs use a `serving.kserve.io/stop: "true"` annotation to fully stop a model (no pods, no revision). **Just setting `minReplicas` is not enough** — Knative honors the stop annotation and will keep the ISVC in `Stopped` state even with `minReplicas: 1`.

### Wake a stopped model
```bash
# Remove the stop annotation (this is the key step)
kubectl annotate isvc <model> -n models serving.kserve.io/stop- --overwrite
# Set minReplicas to spin up the pod
kubectl patch isvc <model> -n models --type merge -p '{"spec":{"predictor":{"minReplicas":1}}}'
```

### Stop a model (spin down completely)
```bash
# Scale to zero AND add stop annotation
kubectl patch isvc <model> -n models --type merge -p '{"spec":{"predictor":{"minReplicas":0}}}'
kubectl annotate isvc <model> -n models serving.kserve.io/stop=true --overwrite
```

### Check readiness
```bash
kubectl get isvc <model> -n models -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
```

### Test pattern (per model)
1. Remove stop annotation → set minReplicas=1
2. Wait for `Ready=True`
3. Run test barrage via gateway (inside gateway pod or from head node via ClusterIP)
4. Set minReplicas=0 → add stop annotation
5. Move to next model
