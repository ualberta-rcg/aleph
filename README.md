<img src="./assets/ua_logo_green_rgb.png" alt="University of Alberta Logo" width="50%" />

# Aleph

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-RKE2-blue.svg)](https://www.rke2.io/)
[![GPU Scheduling](https://img.shields.io/badge/GPU-HAMi-76B900.svg)](https://github.com/Project-HAMi/HAMi)
[![Serving](https://img.shields.io/badge/Serving-KServe%20%2B%20Knative-orange.svg)](https://kserve.github.io/website/latest/)
[![Models](https://img.shields.io/badge/Models-170%2B-blueviolet.svg)](./models/)
[![Docker Hub](https://img.shields.io/docker/v/rkhoja/aleph?label=Docker%20Hub&color=blue)](https://hub.docker.com/r/rkhoja/aleph)

> **170+ science and language models — one endpoint, one key, from protein folds to LLMs.**
>
> *One point. Every model. Infinite unity.*

*Deployed on the [University of Alberta](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html) / [AMII](https://www.amii.ca/) Vulcan environment for multi-model GPU inference*

**Maintained by:** Rahim Khoja ([khoja1@ualberta.ca](mailto:khoja1@ualberta.ca)) and Karim Ali ([kali2@ualberta.ca](mailto:kali2@ualberta.ca))

---

## 📖 Description

**Aleph** is a complete multi-model inference platform — a self-deploying RKE2 Kubernetes cluster, HAMi GPU virtualization, KServe/Knative serving, 170+ model definitions, and a FastAPI gateway that unifies them all behind one OpenAI- and Anthropic-compatible endpoint. Protein structure, genomics, materials, climate, astronomy, medical imaging, and LLMs — one key, one URL, scale-to-zero.

Not a chatbot stack. CERN runs a similar KServe-based platform for physics inference at [ml.cern.ch](https://ml.docs.cern.ch/serving/); Aleph is that idea applied across all research science — AlphaFold alongside Gemma, MACE alongside Qwen, NeuralGCM alongside DeepSeek. The gateway discovers models from the Kubernetes API — a labeled `details.yaml` ConfigMap plus live `InferenceService` state — and routes by model ID to predictor pods through the Knative local gateway. No model names are hardcoded; add a model by applying YAML, and it appears in the catalog. Shaped by the DOE's Genesis Mission push for autonomous science, DeepMind's agent work, Chinese AI labs' open releases, and CERN's production platform.

Models are callable like any other HTTP API — from a Slurm batch job, an agentic pipeline, or a notebook — using a standard OpenAI SDK and a single key. ESMFold to fold a protein, MACE for energy minimization, Aurora for a weather forecast, an LLM to synthesize the results, all through the same endpoint. Idle models drop to zero GPU and wake on first request; science embeddings (SciBERT, ESM2, DNABERT, AstroCLIP) make domain-literature RAG a native use case.

## ✨ Features

- **One endpoint, every model** — OpenAI (`/v1/chat/completions`, `/v1/embeddings`, `/v1/rerank`) and Anthropic (`/v1/messages`) APIs, plus custom science/vision routes (`/v1/science/*`, `/v1/vision/*`, `/v1/dock`, `/v1/forecast`, etc.)
- **Kubernetes-native discovery** — the gateway watches the K8s API for `details.yaml` ConfigMaps (labeled `model-details=true`) and merges live `InferenceService` state; apply YAML and the model appears in the catalog, no restart, nothing hardcoded
- **Science models first** — proteins, DNA, RNA, molecules, materials, weather, astronomy, medical imaging, time-series, and audio alongside general-purpose LLMs
- **Any KServe runtime** — KServe is the orchestration layer, not the engine, so a model card can back onto whatever serves it best: vLLM (most LLMs), Hugging Face/TEI (embeddings, rerank), ONNX Runtime (vision), JAX/Lightning/TensorFlow or a custom FastAPI server.py (science), and NVIDIA NIM (boltz-2, openfold-3). Triton, TorchServe, and TensorFlow Serving are equally deployable when a model calls for them.
- **Fractional GPU scheduling** — HAMi slices each L40S into virtual GPUs (`nvidia.com/gpumem`); many models share one physical card
- **Scale-to-zero + cold-start aware** — idle models drop to zero pods; first request gets a `503 + retry-after` while the pod wakes; agent loops handle this natively
- **Catch-all auth** — accepts `Authorization: Bearer`, `x-api-key`, `api-key`, or `?api_key=`; Tyk normalizes them all
- **Usage accounting** — per-request JSON-lines log (identity, tokens, GPU SKU, node, gpu-seconds) + Prometheus metrics on `/metrics`; rate-limiting via Tyk
- **NFS-backed weights** — model weights on shared NFS PVCs; survive pod and node churn without re-download

## 🚀 Quickstart

Bake the Warewulf overlays, boot the nodes, and the cluster self-deploys; then issue a key and apply model YAML. Full walkthrough — cluster bring-up, secrets, deploying and testing models, and adding a new one — is in **[QUICKSTART.md](./QUICKSTART.md)**.

## 🔬 Model Catalog

The `models/` directory contains 170+ models across scientific and language domains:

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

Each model in `models/<name>/` includes a `details.yaml` card, `inferenceservice.yaml`, `pvc.yaml`, and a `test.py` battery. Adding one is a few files plus `kubectl apply` — see **[QUICKSTART.md](./QUICKSTART.md#-adding-a-model)**.

## 🏗️ Architecture

```
   HPC job / SDK / curl
          │  http(s)  (OpenAI or Anthropic dialect)
          ▼
  ┌─────────────────┐
  │     MetalLB     │  public VIP (L2) advertised out the head node's public NIC;
  │                 │  hands traffic to the Tyk LoadBalancer Service
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │    Tyk OSS      │  catch-all auth (Bearer / x-api-key / api-key / ?api_key=),
  │                 │  rate-limit, JSVM middleware stamps X-Aleph-* identity headers
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  model-gateway  │  FastAPI: OAI⇄Anthropic translation, card-based routing,
  │   (FastAPI)     │  cold-start guard (503 + Retry-After), usage accounting
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │   Istio mesh    │  service mesh Knative programs; cluster-local-gateway routes
  │                 │  by Host header to the live revision — or to the Knative
  │                 │  activator, which holds the request while a cold pod boots
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ KServe ISVC pod │  vLLM / TEI / ONNX / JAX / NIM / custom FastAPI on a
  │                 │  HAMi vGPU slice; weights on NFS PVC
  └─────────────────┘
```

The gateway image is published to [Docker Hub (`rkhoja/aleph`)](https://hub.docker.com/r/rkhoja/aleph) on every push to `main` touching `gateway/**` — tagged `latest` (moving) and `gateway-<sha>` (immutable). Roll out a new build:

```bash
kubectl rollout restart deploy/model-gateway -n models
```

**What boots, in order.** Control-plane nodes carry the full RKE2 auto-deploy manifest set, applied on first boot:

| Manifest | Does |
|---|---|
| `00–01` cert-manager + ClusterIssuer | ACME/TLS for the public endpoint |
| `10` HAMi | vGPU device plugin + scheduler (DaemonSet, `gpu=on` nodes only) |
| `11` node-labeler | DaemonSet detects each worker's GPU/CPU/RAM and stamps `aleph.*` node labels — every usage record carries real hardware provenance |
| `30` NFS | `nfs-models` StorageClass — the default; model weights live here |
| `40–41` MetalLB | L2 load-balancer + VIP IPAddressPool |
| `50–54` Tyk | Redis, OSS gateway, LoadBalancer exposure, API definitions, JSVM middleware |
| `60` Istio | Service mesh + scaffolding the serving stack needs |
| `61–62` Knative + KServe | Scale-to-zero autoscaling and the InferenceService CRD |
| `63` model-gateway | The FastAPI router (runs on control-plane nodes only) |
| `70` RDMA device plugin | Exposes the RoCE NIC as `rdma/roce` so NCCL runs collectives over RDMA — required for multi-GPU tensor-parallel models |

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
