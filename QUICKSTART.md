# Aleph Quickstart

Stand up the cluster, issue a key, then deploy and test models. For what Aleph is
and how the pieces fit together, see the [README](./README.md).

## 🚀 Bring up the cluster

### 1. Clone and configure

```bash
git clone git@github.com:ualberta-rcg/aleph.git && cd aleph
cp .env.example .env          # fill HF_TOKEN, NGC_API_KEY, and TYK_SECRET / TYK_API_SECRET
set -a; source .env; set +a
```

### 2. Prepare and bake Warewulf overlays

Start with the base OS image from [`warewulf-rke2-hami`](https://github.com/ualberta-rcg/warewulf-rke2-hami) (Ubuntu 24.04 + NVIDIA drivers + HAMi runtime + RKE2 pre-baked).

Fill in your site values (`ww-overlays/SITE-VALUES.md`) — VIP, NFS server/path, K8s version, RoCE NIC, ACME email, Tyk secret — then bake the appropriate overlay on top of the base image for each node role:

| Node type | Base image | Overlay | Enables |
|---|---|---|---|
| Control-plane | `warewulf-rke2-hami` | `ww-overlays/overlays/control-plane/` | RKE2 auto-deploy manifests, public VIP netplan/sysctl, `tyk-admin.sh` |
| GPU worker | `warewulf-rke2-hami` | `ww-overlays/overlays/gpu-worker/` | NVIDIA persistence-mode service, RoCE/RDMA kernel modules |
| All nodes | — | `ww-overlays/overlays/common/` | inotify limit bump for dense-pod headroom |

### 3. Boot nodes — the cluster self-deploys

Boot the provisioned nodes. On first boot:
- Control-plane nodes read `etc/rancher/manifests/` and RKE2 applies the full manifest set cluster-wide — cert-manager → HAMi → NFS → MetalLB → Tyk → Istio → Knative → KServe → model-gateway — no deploy script, no SSH push
- GPU worker nodes join the cluster, NVIDIA persistence starts, and the HAMi device plugin schedules onto `gpu=on` nodes automatically

### 4. Post-deploy: secrets and first API key

```bash
# HuggingFace token — used by model init containers
kubectl create secret generic hf-token -n models \
  --from-literal=token="$HF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

# NVIDIA NGC API key — used by NIM containers (boltz-2, openfold-3, …)
kubectl create secret generic ngc-api-key -n models \
  --from-literal=NGC_API_KEY="$NGC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# NGC image-pull secret — needed to pull NIM images from nvcr.io
kubectl create secret docker-registry ngc-registry-secret -n models \
  --docker-server=nvcr.io --docker-username='$oauthtoken' \
  --docker-password="$NGC_API_KEY" --docker-email=you@example.com

# Issue a Tyk API key (see ww-overlays/post-deploy/README.md or gateway/tyk/tyk-keys.sh)
```

### 5. Deploy a model

```bash
kubectl apply -f models/<model>/pvc.yaml
kubectl apply -f models/<model>/details.yaml          # gateway picks it up live
kubectl apply -f models/<model>/inferenceservice.yaml
```

### 6. Test

```bash
# Gateway checks (catalog, health, auth, routing guardrails)
GW_URL=http://<VIP> TYK_KEY=<key> python3 gateway/test.py

# Per-model battery
GW_URL=http://<VIP> TYK_KEY=<key> MODEL=<id> python3 models/<model>/test.py
```

## ➕ Adding a Model

Each model lives in `models/<name>/` and follows one of three patterns — **vLLM chat/LLM**, **custom science server**, or **embedding/rerank/audio** — documented in `models/DETAILS-TEMPLATE-LLM.md`.

**Standard files:**

```
models/<name>/
  details.yaml          # ConfigMap — model card (gateway catalog entry, schema v2)
  inferenceservice.yaml # KServe InferenceService — runtime, init container (weight
                        #   download + venv setup on PVC), server code, resources, scaling
  pvc.yaml              # PersistentVolumeClaim — NFS storage for weights and venv cache
  test.py               # Test battery (copy from models/test.template.py)
  CLAUDE.md             # Optional — model-specific quirks and deployment notes
```

**Steps:**

1. Copy the right `details.yaml` template from `models/DETAILS-TEMPLATE-LLM.md` (Template A for vLLM LLMs, B for custom science servers, C for embeddings/rerank/audio). Fill in all `CHANGEME` fields.
2. Write `inferenceservice.yaml` — the init container handles weight download and venv setup (short-circuits if the PVC already has the artifacts). For vLLM LLMs, prefer `vllm/vllm-openai:v0.20.2` — it's the version pinned across the existing fleet and is cached on the nodes, so staying on it keeps cold starts fast and behavior consistent. Newer tags work; you just lose the cached-layer head start and risk per-model arg drift. For custom science servers, embed the FastAPI server script inline as a ConfigMap in the same file.
3. Write `pvc.yaml` using `storageClassName: nfs-models`. Size generously — the init container caches both weights and the venv so cold starts don't re-download.
4. Copy `models/test.template.py` → `models/<name>/test.py`. Keep only the sections that apply (chat, embeddings, science), update `MODEL` and expected outputs.
5. Deploy and validate:
   ```bash
   kubectl apply -f models/<name>/pvc.yaml
   kubectl apply -f models/<name>/details.yaml
   kubectl apply -f models/<name>/inferenceservice.yaml
   GW_URL=http://<VIP> TYK_KEY=<key> MODEL=<name> python3 models/<name>/test.py
   ```

For HAMi GPU resources: use `nvidia.com/gpumem: "<MiB>"` + `nvidia.com/gpu: "1"` for fractional single-GPU models; use `nvidia.com/gpu: "<N>"` (no `gpumem`) + `--disable-custom-all-reduce` for multi-GPU tensor-parallel models.

The `models/test-model.sh <model> [action]` helper drives apply / recreate / up / status / logs / curl / zero / cycle for a single model from the repo root.
