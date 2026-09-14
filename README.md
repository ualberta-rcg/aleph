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

Gateway releases are built by the repository's CI workflow. Production deployments
pin a specific image version/digest; restarting a Deployment alone does not update
that pin. Keep deployed configuration and boot sources aligned.

The [overlay guide](docs/WW-OVERLAYS.md) describes the deployment layout. Model
manifests and cards live under `models/`; gateway source and tests live under
`gateway/`.

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
