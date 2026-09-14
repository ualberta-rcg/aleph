<p align="center"><img src="./assets/aleph.png" alt="Aleph logo" width="20%" /></p>

<img src="./assets/ua_logo_green_rgb.png" alt="University of Alberta Logo" width="50%" />

# Aleph — The Science Inference Cluster

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-RKE2-blue.svg)](https://www.rke2.io/)
[![GPU Scheduling](https://img.shields.io/badge/GPU-HAMi-76B900.svg)](https://github.com/Project-HAMi/HAMi)
[![Serving](https://img.shields.io/badge/Serving-KServe%20%2B%20Knative-orange.svg)](https://kserve.github.io/website/latest/)
[![Models](https://img.shields.io/badge/Models-100%2B-blueviolet.svg)](./models/)
[![Docker Hub](https://img.shields.io/docker/v/rkhoja/aleph?label=Docker%20Hub&color=blue)](https://hub.docker.com/r/rkhoja/aleph)

> **Over 100 model deployments — one endpoint, one key, from protein folds to LLMs.**
>
> *One point. Every model. Infinite unity.*

*Deployed on the [University of Alberta](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html) / [AMII](https://www.amii.ca/) Vulcan environment for multi-model GPU inference*

**Maintained by:** Rahim Khoja ([khoja1@ualberta.ca](mailto:khoja1@ualberta.ca)) and Karim Ali ([kali2@ualberta.ca](mailto:kali2@ualberta.ca))

---

## 📖 Description

Aleph is a local inference server. It serves AI models much like a web server
serves content: send a request over HTTP and receive text, an image, a prediction,
or another model-specific result. The hosted models run on hardware we operate
on Vulcan.

Compatible tools use the same API formats they already support: change the server
address, supply an Aleph API key, and name the model. A notebook, research pipeline,
browser application, or agent can use the service without managing its own model
weights, software environment, or GPU allocation.

Researchers share running model servers, avoiding repeated setup and loading for
each workflow. The model stays loaded while in use; idle models can release their
GPU resources while retaining their weights on persistent storage. The researcher
chooses the right model and evaluates its results; Aleph handles serving it.

## ✨ Features

- **Science and language models** — protein structure, genomics, materials, weather,
  medical imaging, and other scientific tasks alongside chat, vision, and audio.
- **Compatible APIs** — OpenAI-style chat and embeddings, Anthropic-style messages,
  and model-specific science endpoints. Check each card for supported inputs and features.
- **Flexible runtimes** — KServe manages deployment; vLLM, Text Embeddings
  Inference, NVIDIA NIM, or custom servers execute the models. A new API may need
  a gateway adapter; adding a supported model needs its deployment and card.
- **GPU sharing and scaling** — small models can share a GPU through HAMi, while
  larger models can request multiple devices. Adding workers expands the pool;
  starting more model copies shares demand within that pool. Both need capacity.
- **Always-on or on-demand** — selected models keep a running copy; others scale
  to zero when idle. A wake-up can return `503` with retry guidance, or a capacity
  refusal when the gateway cannot find a suitable placement.
- **Authentication and accounting** — Tyk handles API keys and rate limits; the
  gateway records caller identity, token counts, latency, status, and allocated
  resources, and exposes aggregate metrics. See [Logging and metrics](docs/LOGGING.md)
  for examples, content exclusions, and retention.
- **Persistent weights** — NFS-backed storage allows models to reuse downloaded
  weights across pod and node replacement.

## 🚀 Quickstart

- **Use the hosted service:** browse [models and examples](https://inference.vulcan.alliancecan.ca/),
  use [browser chat](https://llm.vulcan.alliancecan.ca/), or follow the
  [Alliance Aleph guide](https://docs.alliancecan.ca/wiki/aleph) for API access.
- **Deploy your own instance:** [QUICKSTART.md](QUICKSTART.md) covers requirements,
  configuration, provisioning, and first-model validation.
- **Add a model:** [the model workflow](docs/ADD-A-MODEL.md) covers runtime selection,
  deployment, testing, and recording the result.

The hosted service is a proof of concept with shared capacity and no SLA.

## 🔬 Model Catalog

Aleph hosts over 100 model deployments across scientific and language domains:

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

A repository entry does not guarantee that the model is currently served. Use the
[live catalog](https://inference.vulcan.alliancecan.ca/) for availability and each
model's README for its test status and limitations. Authenticated `GET /v1/models`
lists chat models; add `?all=true` for the full catalog. To contribute a deployment,
follow [Add a model](docs/ADD-A-MODEL.md).

## 🏗️ Architecture

```text
  Node-image repo + Aleph overlays + private site configuration
           │  OS, drivers, RKE2, node profiles and role configuration
           ▼
  ┌─────────────────┐
  │    Warewulf     │  builds and delivers the node image and overlays;
  │  provisioning   │  network boot + firstboot prepare each node's role
  └────────┬────────┘
           ├───────────────────────────────────────────┐
           ▼                                           ▼
  ┌─────────────────┐                         ┌─────────────────┐
  │  Control-plane  │  RKE2 servers,           │   GPU workers   │  RKE2 agents,
  │       VMs       │  Kubernetes API, etcd    │ physical nodes  │  NVIDIA runtime
  └─────────────────┘                         └─────────────────┘
    Bootstrap stages platform manifests;        Drivers come from the image;
    RKE2 installs the components below.          model pods use the GPU pool.

   Applications / research jobs / SDK / curl / agents
           │  HTTPS (OpenAI, Anthropic or model-specific API)
           ▼
  ┌─────────────────┐
  │     MetalLB     │  advertises the public service IP over L2;
  │                 │  traffic enters the Traefik LoadBalancer Service
  └────────┬────────┘
           ▼
  ┌─────────────────┐  ◄── cert-manager + Let's Encrypt (ACME HTTP-01)
  │  Traefik (RKE2) │      issue/renew the TLS certificate; Traefik redirects
  │ (TLS terminate) │      HTTP to HTTPS and routes by hostname to internal Tyk
  └────────┬────────┘
           ▼
  ┌─────────────────┐       ┌─────────────────┐
  │    Tyk OSS      │ ◄───► │      Redis      │  key sessions, identity, API
  │ auth + limits   │       │ persistent PVC  │  access and rate-limit state
  └────────┬────────┘       └────────┬────────┘
           │                        └── NFS-backed Redis data
           │  /v1/ and /anthropic/ require keys; root web route is keyless
           │  middleware supplies X-Aleph-* identity headers
           ▼
  ┌─────────────────┐  ◄── model cards (details ConfigMaps) + deployment state
  │  model-gateway  │      discovered through Kubernetes API watches
  │   (FastAPI)     │
  └────────┬────────┘  ──► usage JSONL: per-replica files on a separate NFS PVC
           │           ──► /metrics: aggregate request/accounting counters
           │  API translation, model routing and cold-start capacity guard;
           │  may return 503 + retry guidance before forwarding
           ▼
  ┌─────────────────┐
  │   Istio mesh    │  Knative configures the internal service routes;
  │  local gateway  │  requests target the selected model revision
  └────────┬────────┘
           ├── ready revision path ─────────────────────┐
           ▼                                           │
  ┌─────────────────┐                                  │
  │    Knative      │  activation/buffering when         │
  │    activator    │  included in the traffic path      │
  └────────┬────────┘                                  │
           ◄───────────────────────────────────────────┘
           ▼
  ┌─────────────────┐  ◄── KServe + Knative controllers manage services,
  │ Model predictor │      revisions and desired replica counts
  │       pod       │  ◄── Kubernetes + HAMi place pods and allocate GPUs
  └────────┬────────┘
           │  queue-proxy → serving runtime: vLLM / TEI / NIM / custom server
           │  shared GPU allowance or multiple whole GPUs, as configured
           ▼
  ┌─────────────────┐
  │   Model PVCs    │  NFS-backed weights, caches and prepared environments;
  │ persistent NFS  │  retained when the model scales to zero or a pod is replaced
  └─────────────────┘

  KServe/Knative controllers and HAMi manage the pods; they are not extra
  inference-request hops. Tyk's admin-command audit file is separate from
  Redis and the gateway usage ledger. Physical GPU telemetry is separate
  from gateway accounting metrics.
```

Checked against the running deployment and boot-source documentation on
**2026-09-13**. Ingress and the gateway run on control-plane nodes; GPU predictors
run on workers. Site addresses and hardware counts stay in private notes.

Gateway releases are built by the repository's CI workflow. Production deployments
pin a specific image version/digest; restarting a Deployment alone does not update
that pin. Keep deployed configuration and boot sources aligned.

The [overlay guide](docs/WW-OVERLAYS.md) describes provisioning and storage;
[Kubernetes](docs/KUBERNETES.md) covers serving and scaling. Model manifests and
cards live under `models/`; gateway source and tests live under `gateway/`.
See [Tyk](docs/TYK-USERS.md) and [Logging and metrics](docs/LOGGING.md) for key
management, usage history and GPU measurements.

## 📚 Docs

| Guide | Purpose |
|---|---|
| [Quickstart](QUICKSTART.md) | Deploy an instance |
| [Add a model](docs/ADD-A-MODEL.md) | Our deployment and validation workflow |
| [Endpoints](docs/ENDPOINTS.md) | API paths and client configuration |
| [API keys](docs/TYK-USERS.md) | Authentication and identity |
| [Logging and metrics](docs/LOGGING.md) | Recorded data, examples, retention, and usage reports |
| [Warewulf](docs/WW-OVERLAYS.md) | Overlays, site settings, and storage |
| [Kubernetes](docs/KUBERNETES.md) | Serving components, placement, and model lifecycle |
| [System](docs/SYSTEM.md) | Boot integration, node services, and GPU/RDMA support |
| [Gateway reference](gateway/README.md) | Routing and model-card behavior |

## 🔗 References

- [University of Alberta Research Computing](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html)
- [Alberta Machine Intelligence Institute (AMII)](https://www.amii.ca/)
- [Warewulf](https://warewulf.org/docs/main/)
- [KServe](https://kserve.github.io/website/)
- [HAMi](https://project-hami.io/docs/)

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
