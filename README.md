<p align="center"><img src="./assets/aleph.png" alt="Aleph logo" width="20%" /></p>

<img src="./assets/ua_logo_green_rgb.png" alt="University of Alberta Logo" width="50%" />

# Aleph — The Science Inference Cluster

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-RKE2-blue.svg)](https://www.rke2.io/)
[![GPU Scheduling](https://img.shields.io/badge/GPU-HAMi-76B900.svg)](https://github.com/Project-HAMi/HAMi)
[![Serving](https://img.shields.io/badge/Serving-KServe%20%2B%20Knative-orange.svg)](https://kserve.github.io/website/latest/)
[![Models](https://img.shields.io/badge/Models-100%2B-blueviolet.svg)](./models/)
[![Docker Hub](https://img.shields.io/docker/v/rkhoja/aleph?label=Docker%20Hub&color=blue)](https://hub.docker.com/r/rkhoja/aleph)

> **Over a hundred science and language models — one endpoint, one key, from protein folds to LLMs.**
>
> *One point. Every model. Infinite unity.*

**Live service:** [`https://inference.vulcan.alliancecan.ca`](https://inference.vulcan.alliancecan.ca) — the landing page is public; every API route (including `GET /v1/models`) requires an Aleph API key.

*Deployed on the [University of Alberta](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html) / [AMII](https://www.amii.ca/) Vulcan environment for multi-model GPU inference*

**Maintained by:** Rahim Khoja ([khoja1@ualberta.ca](mailto:khoja1@ualberta.ca)) and Karim Ali ([kali2@ualberta.ca](mailto:kali2@ualberta.ca))

---

## 📖 What it is

Aleph is an inference server: it serves AI models over HTTP the way a web server serves pages. It speaks the **OpenAI** and **Anthropic** API formats natively, so existing SDKs and agent harnesses work by changing the base URL and supplying an Aleph key. Requests are routed to a running copy of the requested model; results come back through the same API.

The catalog spans **over a hundred models**, and most of them are specialist science tools — protein structure (AlphaFold2, Boltz-2, ESMFold), genomics (DNABERT-2, Borzori, Enformer), materials (MACE, CHGNet), weather/climate (Aurora, GraphCast, NeuralGCM), astronomy, medical imaging, vision, audio, and time-series — alongside general-purpose chat models, which make up roughly one in six of the catalog. The authoritative list is the live one: `GET /v1/models` with a key (`?all=true` for the full catalog; the default response lists chat models).

It exists because serving inference as shared infrastructure beats every researcher self-hosting: without it, each workflow must fetch weights, build environments, hold a GPU allocation, and load the model before the first call. With Aleph, a Slurm job — or a notebook, agent, or browser chat — calls one endpoint for one step of its work. Models stay loaded between requests; idle ones release their GPUs entirely and reload on demand.

It runs on hardware we operate (the Vulcan cluster), so model inference stays local to the cluster and your data never leaves it. Usage accounting is metadata-only: per-request records carry identity, model, token counts, latency, and allocated resources — never prompts, completions, or uploads.

## ✨ Features

- **One endpoint, every model** — OpenAI (`/v1/chat/completions`, `/v1/embeddings`, `/v1/rerank`, …) and Anthropic (`/v1/messages`, `/v1/messages/count_tokens`) APIs, plus custom science/vision routes (`/v1/science/*`, `/v1/vision/*`, `/v1/dock`, `/v1/forecast`, …)
- **Kubernetes-native discovery** — the gateway watches the K8s API for model-card ConfigMaps (labeled `model-details=true`) and merges live `InferenceService` state; apply YAML and the model appears in the catalog, no restart, nothing hardcoded
- **Any KServe runtime** — KServe orchestrates, the model card picks the engine: vLLM (most LLMs), Hugging Face TEI (embeddings/rerank), NVIDIA NIM, ONNX Runtime, JAX/TensorFlow, or a small custom server around researcher code
- **Fractional and multi-GPU scheduling** — HAMi slices each GPU into virtual devices (`nvidia.com/gpumem` for a memory slice, whole devices for large models, several devices for tensor-parallel ones)
- **Scale-to-zero, cold-start aware** — idle models drop to zero pods; a first request gets `503 model_scaled_to_zero` with an ETA and `Retry-After` while the pod wakes, or `503 insufficient_capacity` when the gateway's live capacity simulation finds no room. A small roster of high-demand models stays always-on (min ≥ 1 replica)
- **Catch-all auth** — one key, sent however your SDK likes: `Authorization: Bearer`, `x-api-key`, `api-key`, `x-goog-api-key`, or query string; Tyk normalizes them all before auth and rate-limiting
- **Usage accounting** — durable per-request JSON-lines ledger (identity, tokens, status, latency, GPU allocation, derived GPU-seconds; key fingerprints, not keys) plus Prometheus `/metrics`; content is never logged
- **NFS-backed weights** — model weights (and some prepared Python environments) live on shared NFS PVCs; copies share files, pods and nodes come and go without re-downloading

## 🚀 Quickstart

Two different starts:

- **Use the service** — get a key, point your SDK at the endpoint: see **[docs/RESEARCHER-GUIDE.md](./docs/RESEARCHER-GUIDE.md)** and **[docs/ENDPOINTS.md](./docs/ENDPOINTS.md)**
- **Stand up your own** — bake the Warewulf overlays, boot the nodes, and the cluster self-deploys from the numbered RKE2 auto-deploy manifests; then issue a key and apply model YAML. Full walkthrough: **[QUICKSTART.md](./QUICKSTART.md)**

## 🔬 Model Catalog

The `models/` directory holds model definitions across scientific and language domains:

| Domain | Examples |
|---|---|
| **Protein / Structural biology** | AlphaFold2, Boltz-2, ESMFold, ESM2, ESM-C 300M, ProstT5, LigandMPNN, DiffDock, SaProt |
| **Genomics / DNA / RNA** | Nucleotide Transformer, DNABERT-2, GENA-LM, Borzoi, Enformer, Caduceus, RNAbert |
| **Materials / Chemistry** | MACE-MH-1, MACE-MP, CHGNet, ChemBERTa, MatterSim, CrystalLLM, ChemGPT |
| **Weather / Climate** | Aurora, GraphCast, FourCastNet3, Pangu-Weather, NeuralGCM, ClimaX, FengWu |
| **Astronomy** | AstroCLIP, AstroPT, AstroSage, Zoobot |
| **Medical / Imaging** | MedGemma, BiomedCLIP, TotalSegmentator, MedSAM, ClinicalBERT |
| **Vision / 3D** | FLUX.1, Kandinsky 3, DUSt3R, MASt3R, YOLOv8, Mask R-CNN, Depth Anything |
| **Time-series / Audio** | Chronos-Bolt, TimesFM, TTM, XTTS-v2, BirdNET, CLAP |
| **Language models** | Gemma 3/4, Qwen 3/3.5/3.6, GLM-4/Z1, GPT OSS 20B/120B, DeepSeek R1, Command-R |
| **Science NLP** | SciBERT, BioGPT, SciNCL, SpecTer2, OceanGPT, GeoGalactica, OpenBioLLM |

The catalog grows continuously and not every model receives the same testing attention — per-model state is tracked operationally, and the deployed set at any moment is what `GET /v1/models` reports. Each model in `models/<name>/` carries `details.yaml` (the card), `inferenceservice.yaml`, `pvc.yaml`, and a `test.py` battery; adding one is a few files plus `kubectl apply` — see **[docs/MODEL-DEPLOY-PLAYBOOK.md](./docs/MODEL-DEPLOY-PLAYBOOK.md)**.

## 🏗️ Architecture

```
   HPC job / SDK / curl
          │  HTTPS  (OpenAI or Anthropic dialect)
          ▼
  ┌─────────────────┐
  │     MetalLB     │  public VIP (L2) advertised out the head node's public NIC;
  │                 │  hands traffic to the Traefik LoadBalancer Service
  └────────┬────────┘
           ▼
  ┌─────────────────┐  ◄── cert-manager + Let's Encrypt (ACME HTTP-01) issues the
  │  Traefik (RKE2) │      public TLS cert; Traefik terminates HTTPS here, redirects
  │ (TLS terminate) │      :80 → :443, and routes by Host header to the Tyk Service
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │    Tyk OSS      │  catch-all auth (Bearer / x-api-key / api-key / x-goog-api-key / ?api_key),
  │                 │  rate-limit, JSVM middleware stamps X-Aleph-* identity headers
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  model-gateway  │  FastAPI: OAI⇄Anthropic translation, card-based routing,
  │   (FastAPI)     │  cold-start guard (503 + Retry-After), usage accounting
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │   Istio mesh    │  service mesh Knative programs; knative-local-gateway routes
  │                 │  by Host header to the live revision — or to the Knative
  │                 │  activator, which holds the request while a cold pod boots
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ KServe ISVC pod │  vLLM / TEI / ONNX / JAX / NIM / custom FastAPI on a
  │                 │  HAMi vGPU slice; weights on NFS PVC
  └─────────────────┘
```

**What boots, in order.** Control-plane nodes carry the full RKE2 auto-deploy manifest set, applied on first boot:

| Manifest | Does |
|---|---|
| `00–01` cert-manager + ClusterIssuer | ACME/TLS for the public endpoint |
| `09` gpu-autolabel | labels GPU-bearing workers `gpu=on`, gating the GPU stack below |
| `10` HAMi | vGPU device plugin + scheduler (DaemonSet, `gpu=on` nodes only) |
| `11` node-labeler | DaemonSet detects each worker's GPU/CPU/RAM and stamps `aleph.*` node labels — every usage record carries real hardware provenance |
| `30` NFS | `nfs-models` StorageClass — the default; model weights live here |
| `40–43` MetalLB + Traefik | L2 load-balancer + VIP pool, public Traefik service and edge routing config |
| `49–56` Tyk | Redis (NFS-persistent), OSS gateway, API definitions, JSVM middleware, edge routes + TLS Certificate |
| `60` Istio | Service mesh + scaffolding the serving stack needs |
| `61–62` Knative + KServe | Scale-to-zero autoscaling and the InferenceService CRD |
| `63` model-gateway | The FastAPI router (runs on control-plane nodes only) |
| `70` RDMA device plugin | Exposes the RoCE NIC as `rdma/roce` so NCCL runs collectives over RDMA — used by multi-GPU tensor-parallel models |
| `80` model PVs | Static PV rebinds restoring the model-weight volumes onto the NFS backend |

**Gateway releases.** The gateway image is published to [Docker Hub (`rkhoja/aleph`)](https://hub.docker.com/r/rkhoja/aleph) on every push to `main` touching `gateway/**` — tagged `latest` (moving) and `gateway-<sha>` (immutable). Production pins an immutable tag: roll out by bumping the pin in `63-model-gateway.yaml` and `kubectl set image deploy/model-gateway -n models gateway=rkhoja/aleph:gateway-<sha>`. (`imagePullPolicy: IfNotPresent`, so a bare `rollout restart` does *not* pick up a new build.)

## 📚 Docs

| Doc | What |
|---|---|
| [QUICKSTART.md](./QUICKSTART.md) | Bring up the whole platform from Warewulf bake to first model |
| [docs/RUNBOOK.md](./docs/RUNBOOK.md) | Day-2 operations: gateway rollouts, keys, storage, teardown |
| [docs/MODEL-DEPLOY-PLAYBOOK.md](./docs/MODEL-DEPLOY-PLAYBOOK.md) | The per-model deploy loop and standards |
| [docs/RESEARCHER-GUIDE.md](./docs/RESEARCHER-GUIDE.md) | Using Aleph: choosing models, cold starts, reproducibility |
| [docs/ENDPOINTS.md](./docs/ENDPOINTS.md) | Full endpoint surface + client configs |
| [gateway/README.md](./gateway/README.md) | Gateway internals: cards, routing, translation, metrics |
| [models/CLAUDE.md](./models/CLAUDE.md) | Per-model directory contract |
| [docs/WW-OVERLAYS.md](./docs/WW-OVERLAYS.md) | Overlay structure, manifest index, boot self-ordering |

## 🧪 Status

Aleph is a proof of concept with real researchers, jobs, and services on it. There are no SLAs or guaranteed capacity; what's offered reflects the hardware allocated to the service. Usage is metered (tokens and GPU-time) but not quota-enforced — API keys carry rate limits only.

## 🔗 References

- [University of Alberta Research Computing](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html)
- [Alberta Machine Intelligence Institute (AMII)](https://www.amii.ca/)
- [Digital Research Alliance of Canada](https://alliancecan.ca/)
- [HAMi — Heterogeneous AI Computing Virtualization Middleware](https://github.com/Project-HAMi/HAMi)
- [WareWulf RKE2 + Hami Node Image](https://github.com/ualberta-rcg/warewulf-rke2-hami)

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
