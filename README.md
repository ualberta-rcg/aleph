<img src="./assets/ua_logo_green_rgb.png" alt="University of Alberta Logo" width="50%" />

# Aleph

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-RKE2-blue.svg)](https://www.rke2.io/)
[![GPU Scheduling](https://img.shields.io/badge/GPU-HAMi-76B900.svg)](https://github.com/Project-HAMi/HAMi)
[![Serving](https://img.shields.io/badge/Serving-KServe%20%2B%20Knative-orange.svg)](https://kserve.github.io/website/latest/)
[![Models](https://img.shields.io/badge/Models-170%2B-blueviolet.svg)](./models/)
[![Docker Hub](https://img.shields.io/docker/v/rkhoja/aleph?label=Docker%20Hub&color=blue)](https://hub.docker.com/r/rkhoja/aleph)

> **170+ science and language models — one endpoint, one key, from protein folds to LLMs.**

*Deployed on the [University of Alberta](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html) / [AMII](https://www.amii.ca/) Vulcan environment for multi-model GPU inference*

**Maintained by:** Rahim Khoja ([khoja1@ualberta.ca](mailto:khoja1@ualberta.ca)) and Karim Ali ([kali2@ualberta.ca](mailto:kali2@ualberta.ca))

---

## 📖 Description

**Aleph** is a card-driven inference platform for research clusters. 170+ models — protein structure, genomics, materials simulation, climate forecasting, astronomy, medical imaging, and LLMs — all served behind a single OpenAI- and Anthropic-compatible endpoint with per-request usage accounting, fairshare, and scale-to-zero.

This is not a chatbot stack. CERN runs a similar KServe-based platform at [ml.cern.ch](https://ml.docs.cern.ch/serving/) for physics inference; Aleph is the same idea applied broadly to research science — AlphaFold alongside Gemma, MACE alongside Qwen, NeuralGCM alongside DeepSeek. Each model publishes a `details.yaml` card; the gateway watches those cards and builds a live catalog without a single model name hardcoded in the routing layer. Inspired by the pace of model releases from DeepMind, Anthropic, and Chinese AI labs, the catalog is designed to grow without touching the gateway.

Aleph is built to sit **next to** a Slurm cluster, not replace it. Call any model from a batch job using your existing OpenAI SDK. Models scale to zero when idle and wake on first request — no idle GPU burn between jobs. Science embeddings (protein, genomic, astronomical, materials) make RAG over domain literature a first-class use case alongside generation and prediction.

The cluster nodes are built on the [`warewulf-rke2-hami`](https://github.com/ualberta-rcg/warewulf-rke2-hami) stateless image. Each node type — control-plane and GPU worker — gets a different overlay baked in; boot a node and it joins its role automatically. When you need more batch capacity and less inference, reprovision GPU worker nodes back to the Slurm image. The same physical hardware serves both worlds without reinstallation.

## ✨ Features

- **One endpoint, every model** — OpenAI (`/v1/chat/completions`, `/v1/embeddings`) and Anthropic (`/v1/messages`) APIs, plus custom science routes (`/v1/science/predict`, `/v1/dock`, `/v1/forecast`, etc.)
- **Card-driven catalog** — each model is a `details.yaml` ConfigMap; the gateway watches cards live, no restarts needed to add a model
- **Science models first** — proteins, DNA, RNA, molecules, materials, weather, astronomy, medical imaging, time-series, and audio alongside general-purpose LLMs
- **Fractional GPU scheduling** — HAMi slices each L40S into virtual GPUs (`nvidia.com/gpumem`); many models share one physical card
- **Scale-to-zero + cold-start aware** — idle models drop to zero pods; first request gets a `503 + retry-after` while the pod wakes; agent loops handle this natively
- **HPC-adjacent** — call models from Slurm jobs with a standard OpenAI SDK; designed for the [Digital Research Alliance of Canada](https://alliancecan.ca/) ecosystem
- **Catch-all auth** — accepts `Authorization: Bearer`, `x-api-key`, `api-key`, or `?api_key=`; Tyk normalizes them all
- **Elastic nodes** — bake and boot a new GPU worker node and it auto-joins the pool; reprovision to Slurm when batch capacity is needed instead
- **Usage accounting / fairshare** — per-request JSON-lines log (identity, tokens, GPU SKU, node, gpu-seconds) + Prometheus metrics on `/metrics`
- **NFS-backed weights** — model weights on shared NFS PVCs; survive pod and node churn without re-download

## 🚀 Quickstart

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

## 🔬 Model Catalog

The `models/` directory contains 170+ models across scientific and language domains:

| Domain | Examples |
|---|---|
| **Protein / Structural biology** | AlphaFold2, Boltz-2, ESMFold, ESM2, ESM-C, ProtTrans, LigandMPNN, DiffDock, SaProt |
| **Genomics / DNA / RNA** | Nucleotide Transformer, DNABERT-2, GENA-LM, Borzoi, Enformer, Caduceus, RNAbert |
| **Materials / Chemistry** | MACE-MH-1, MACE-MP, CHGNet, ChemBERTa, MatterSim, CrystalLLM, ChemGPT |
| **Weather / Climate** | Aurora, GraphCast, FourCastNet3, Pangu-Weather, NeuralGCM, ClimaX, FengWu |
| **Astronomy** | AstroCLIP, AstroPT, AstroSage, Zoobot |
| **Medical / Imaging** | MedGemma, BiomedCLIP, TotalSegmentator, MedSAM, ClinicalBERT |
| **Vision / 3D** | FLUX.1, Kandinsky 3, DUSt3R, MASt3R, YOLOv8, Mask R-CNN, Depth Anything |
| **Time-series / Audio** | Chronos-Bolt, TimesFM, TTM, XTTS-v2, BirdNET, CLAP |
| **Language models** | Gemma 3/4, Qwen 3/3.5/3.6, GLM-4/Z1, GPT OSS 20B/120B, DeepSeek R1, Command-R |
| **Science NLP** | SciBERT, BioGPT, SciNCL, SpecTer2, OceanGPT, GeoGalactica, OpenBioLLM |

Each model in `models/<name>/` includes a `details.yaml` card, `inferenceservice.yaml`, `pvc.yaml`, and a `test.py` battery.

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
2. Write `inferenceservice.yaml` — the init container handles weight download and venv setup (short-circuits if the PVC already has the artifacts). For vLLM LLMs use `vllm/vllm-openai:v0.20.2`. For custom science servers, embed the FastAPI server script inline as a ConfigMap in the same file.
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

## 🏗️ Architecture

```
   HPC job / SDK / curl
          │  http(s)  (OpenAI or Anthropic dialect)
          ▼
  ┌─────────────────┐
  │     MetalLB     │  public VIP (L2), hands traffic to Tyk LoadBalancer
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │    Tyk OSS      │  catch-all auth, rate-limit, stamps X-Aleph-* identity headers
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  model-gateway  │  FastAPI: OAI⇄Anthropic translation, card routing,
  │   (FastAPI)     │  cold-start guard, usage accounting
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ Istio / Knative │  routes by Host header to live revision or activator (scale-to-zero)
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ KServe ISVC pod │  vLLM / custom FastAPI on a HAMi vGPU slice (NFS weights)
  └─────────────────┘
```

The gateway image is published to [Docker Hub (`rkhoja/aleph`)](https://hub.docker.com/r/rkhoja/aleph) on every push to `main` touching `gateway/**` — tagged `latest` (moving) and `gateway-<sha>` (immutable). Roll out a new build:

```bash
kubectl rollout restart deploy/model-gateway -n models
```

## 🤖 Agentic Research

Aleph is designed as infrastructure for autonomous research workflows. An agent running on the Alliance cluster can call any model as a standard HTTP tool from inside a Slurm job — ESMFold to fold a candidate protein, MACE-MH-1 for energy minimization, Nucleotide Transformer for genomic embeddings, Aurora for a weather forecast, and an LLM to synthesize the results — all through one authenticated endpoint.

Models wake on first call and return to zero between steps, so a multi-step agentic pipeline pays for GPU time only when a model is actually running. Science embedding models (SciBERT, ESM2, DNABERT, AstroCLIP, MatSciBERT, SciNCL) make RAG over domain literature a native capability. Cold-start latency is documented in each model card and the gateway returns `503 + Retry-After` that well-behaved clients handle automatically.

This vision — autonomous agents using HPC batch resources and live inference models interchangeably — was shaped by work at DeepMind, Anthropic, CERN, and Chinese AI research labs, and by the Alliance's goal of making national research infrastructure useful to the next generation of agentic science.

## 🌐 Elastic Cluster

Aleph scales by reprovisioning. The base OS image from [`warewulf-rke2-hami`](https://github.com/ualberta-rcg/warewulf-rke2-hami) contains Ubuntu 24.04, NVIDIA drivers, HAMi runtime, and RKE2. Each node type gets a different overlay:

- **Control-plane nodes** — carry the RKE2 auto-deploy manifests that bootstrap the entire platform stack and the public VIP network config; boot one and the cluster comes up
- **GPU worker nodes** — carry NVIDIA persistence-mode and RoCE/RDMA kernel modules; boot one and it joins the GPU pool automatically, no `kubectl join`

**To add inference capacity:** provision a new GPU worker with the `warewulf-rke2-hami` image + `gpu-worker` overlay → it joins on boot.

**To shift to HPC batch:** reprovision those same GPU workers with the Slurm node image (or a Proxmox VM) → capacity returns to batch scheduling. No hardware change, no reinstall.

## 🔭 Why "Aleph"?

Borges' 1945 story describes a point in a Buenos Aires cellar that contains every other point in space — gaze in and you see the whole universe at once, from every angle, without overlap. Cantor's ℵ₀ is the smallest infinity: countless things addressed as one. Frederik Pohl's *Alpha-Aleph* (*The Gold at the Starbow's End*) is the destination a civilization aims its best work at. This platform is all three: one URL that reaches every model, an ever-growing catalog addressed as a single endpoint, and the coordinate researchers and autonomous agents point their jobs at.

*One point. Every model. Infinite unity.*

## 🔗 References

- [University of Alberta Research Computing](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html)
- [Alberta Machine Intelligence Institute (AMII)](https://www.amii.ca/)
- [Digital Research Alliance of Canada](https://alliancecan.ca/)
- [HAMi — Heterogeneous AI Computing Virtualization Middleware](https://github.com/Project-HAMi/HAMi)
- [warewulf-rke2-hami — Node OS image](https://github.com/ualberta-rcg/warewulf-rke2-hami)
- [KServe](https://kserve.github.io/website/latest/)
- [Knative Serving](https://knative.dev/docs/)
- [RKE2](https://docs.rke2.io/)
- [CERN ML Platform](https://ml.docs.cern.ch/serving/)

---

## 🤝 Support

Many Bothans died to bring us this information. This project is provided as-is, but reasonable questions may be answered based on my coffee intake or mood. ;)

Feel free to open an issue or email **[khoja1@ualberta.ca](mailto:khoja1@ualberta.ca)** or **[kali2@ualberta.ca](mailto:kali2@ualberta.ca)** for U of A related deployments.

## 📜 License

This project is released under the **MIT License** — use it, modify it, distribute it, include it in proprietary software. Keep the copyright notice. That's it.

**Full license text:** [MIT License](./LICENSE)

## 🧠 About University of Alberta Research Computing

The [Research Computing Group](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html) supports high-performance computing, data-intensive research, and advanced infrastructure for researchers at the University of Alberta and across Canada.

We help design and operate compute environments that power innovation — from AI training clusters to national research infrastructure.
