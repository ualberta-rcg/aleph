<img src="./assets/ua_logo_green_rgb.png" alt="University of Alberta Logo" width="50%" />

# Aleph

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-RKE2-blue.svg)](https://www.rke2.io/)
[![GPU Scheduling](https://img.shields.io/badge/GPU-HAMi-76B900.svg)](https://github.com/Project-HAMi/HAMi)
[![Serving](https://img.shields.io/badge/Serving-KServe%20%2B%20Knative-orange.svg)](https://kserve.github.io/website/latest/)

> **One gateway, 170+ models — OpenAI- and Anthropic-compatible inference on a self-deploying RKE2/HAMi/KServe stack.**

*Deployed on the University of Alberta / AMII Vulcan environment for multi-model GPU inference.*

**Maintained by:** Rahim Khoja ([khoja1@ualberta.ca](mailto:khoja1@ualberta.ca)) and Karim Ali ([kali2@ualberta.ca](mailto:kali2@ualberta.ca))

---

## 📖 Description

**Aleph** is an inference platform repository for operating a Kubernetes-based model serving stack with fractional GPU scheduling.

> *One endpoint, every model.* Aleph turns a rack of GPUs into a self-healing, scale-to-zero inference cloud — speaking both the OpenAI and Anthropic dialects — so researchers point their existing SDKs at a single URL and Aleph handles the auth, routing, GPU packing, cold-starts, and accounting underneath. Provision the nodes and the platform builds itself; idle models fall to zero and wake on demand; every request is metered for fairshare. No per-model servers to babysit, no GPU left stranded.

It combines:
- **RKE2** for cluster runtime,
- **Warewulf** for stateless node provisioning,
- **HAMi** for vGPU slicing and scheduling,
- **KServe + Knative** for model services and scale-to-zero,
- **Tyk OSS** for key management and API gateway controls,
- **FastAPI gateway** with OpenAI and Anthropic compatible endpoints.

Unlike a typical "chatbot" gateway, Aleph is **science-first**. The catalog spans 170+ models — large language and reasoning models, yes, but also the AI/ML *foundation models* researchers actually run: protein folding (AlphaFold2, ESMFold, Boltz-2, OpenFold), genomics (Nucleotide Transformer, DNABERT, Geneformer), weather & climate (GraphCast, Aurora, FourCastNet, Pangu-Weather), materials & chemistry (MACE, MatterGen, CHGNet), astronomy, medical imaging, and time-series forecasting. Each model is **card-driven**: its `details.yaml` declares its own input/output schema and endpoints, so a model can speak plain OpenAI/Anthropic *or* expose a custom route (e.g. AlphaFold2 takes a sequence at `/v1/science/predict` and returns a PDB) — all behind the same authenticated URL.

It is designed to live **next to an HPC cluster**: instead of every Slurm job loading a multi-gigabyte model onto a scarce GPU, jobs make a request to Aleph's single endpoint with their existing SDK or a `curl`, and Aleph scales the model up (or reuses a warm one), runs inference on a fractional GPU slice, scales back to zero when idle, and meters the call for fairshare. One shared, always-on inference fabric for a whole cluster of users.

The repo includes the Warewulf overlays + RKE2 auto-deploy manifests (`ww-overlays/`), model cards, gateway logic, and validation harnesses used to run the stack reproducibly. The platform is fully declarative: bake the overlays into the node image, provision, and the cluster brings itself up.

## ✨ Features

- **One endpoint, every model** — OpenAI + Anthropic API compatibility in a single gateway
- **Card-driven catalog** — models self-describe (schema, endpoints, scaling) via `details.yaml`; no model names hardcoded in the gateway
- **Science models welcome** — custom non-OpenAI routes (e.g. sequence → structure) alongside chat/reasoning, multimodal, embeddings, rerank, TTS, forecasting
- **Fractional GPU scheduling** with HAMi (`nvidia.com/gpumem` + `nvidia.com/gpu`) — pack many models per physical GPU
- **Scale-to-zero + cold-start aware** — idle models drop to zero, wake on demand, with a "call back in a bit" response while warming
- **HPC-adjacent by design** — call it from Slurm jobs with your existing SDK; offload model serving off your batch GPUs
- **Catch-all auth** — accepts keys via OpenAI `Authorization: Bearer`, Anthropic `x-api-key`, Azure `api-key`, or query param; Tyk normalizes them
- **Usage accounting / fairshare** — per-request JSON-lines log (identity, tokens, GPU SKU, node, gpu-seconds) + Prometheus metrics
- **Fully declarative provisioning** — Warewulf overlays + RKE2 auto-deploy manifests; bake the image, boot the node, cluster self-deploys
- **NFS-backed model persistence** so weights survive reprovisioning

## 🏗️ Architecture

A request enters once at the public VIP and is handed down a chain of single-responsibility layers:

```
   HPC job / SDK / curl
          │  http(s)  (OpenAI or Anthropic dialect)
          ▼
  ┌─────────────────┐
  │     MetalLB     │  owns the public VIP (L2) on the control-plane NIC,
  │   (public VIP)  │  hands it to the Tyk LoadBalancer service
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │    Tyk OSS      │  API gateway: catch-all auth, rate-limit, and stamps
  │ (auth + ident.) │  X-Aleph-* identity headers (JSVM middleware)
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  model-gateway  │  FastAPI: OpenAI⇄Anthropic translation, card-based
  │   (FastAPI)     │  routing, cold-start guard, usage accounting
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │      Istio      │  Knative's network layer: routes by Host header to the
  │ (ingress/mesh)  │  right model, and to the activator when scaled to zero
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ Knative + KServe│  InferenceService → revision → autoscaling / scale-to-zero
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  Predictor pod  │  vLLM / custom server on a HAMi vGPU slice (NFS weights)
  └─────────────────┘
```

| Layer | What it does | Why it's here |
|---|---|---|
| **Warewulf** | Stateless node provisioning (OS, NVIDIA driver, RKE2, HAMi baked into the image) | Reproducible, disposable nodes — rebuild a worker from scratch in minutes |
| **RKE2** | The Kubernetes distribution; reads `/etc/rancher/manifests/` and self-applies the stack | No external CD; the cluster deploys itself on boot |
| **MetalLB** | Bare-metal `LoadBalancer` — claims the public VIP via L2 and assigns it to Tyk | Gives the cluster a single stable public IP without a cloud LB |
| **Tyk OSS** | API gateway at the edge: authenticates keys (catch-all), rate-limits, injects identity | Front door — one auth/quota point for every model |
| **model-gateway** | FastAPI app: translates OpenAI⇄Anthropic, routes by model card, guards cold starts, writes usage records | The brain — turns one API surface into 170 different backends |
| **Istio** | The networking layer Knative runs on. Knative programs an Istio ingress gateway that routes each request **by `Host` header** to the correct model's revision, and to the Knative **activator** when a model is scaled to zero (buffering the request until a pod is up) | This is the mesh that makes scale-to-zero and per-model routing actually work — without it, Knative has nothing to route through |
| **Knative Serving** | Per-model autoscaling, revisions, and **scale-to-zero** | Idle models cost zero GPU; traffic wakes them |
| **KServe** | The `InferenceService` CRD that wraps a model server (vLLM/custom) on top of Knative | Declarative model deployments — one YAML per model |
| **HAMi** | vGPU scheduler + device plugin; slices each physical GPU (`nvidia.com/gpumem`) | Pack many models onto few GPUs instead of one-model-per-card |
| **cert-manager** | ACME/TLS automation | HTTPS for the public endpoint |
| **NFS** | Shared model-weight storage (`StorageClass`) | Weights persist across pod/node churn; no re-download |

> **Where Istio fits (the part that's easy to miss):** clients never talk to Istio directly and you rarely configure it by hand — it's the *internal* router Knative drives. The model-gateway forwards to `…knative-local-gateway…` with the target model's hostname, and Istio resolves that to the live revision (or the activator for a cold model). It's the connective tissue between "pick a model" (gateway) and "run the model" (KServe pod).

## 🚀 Quickstart

### 1) Clone and set secrets

```bash
git clone git@github.com:ualberta-rcg/aleph.git
cd aleph
cp .env.example .env
# fill HF_TOKEN and TYK_SECRET/TYK_API_SECRET
set -a; source .env; set +a
```

### 2) Provision via Warewulf — the platform self-deploys

Fill in your site values (`ww-overlays/SITE-VALUES.md`), then bake each overlay into the
Warewulf image for its node role and provision:

| Overlay | Baked on |
|---|---|
| `ww-overlays/overlays/common/` | all nodes |
| `ww-overlays/overlays/control-plane/` | control-plane nodes (RKE2 auto-deploy manifests + public VIP) |
| `ww-overlays/overlays/gpu-worker/` | GPU workers |

On boot, RKE2 applies the manifests and stands up cert-manager, HAMi, NFS, MetalLB, Tyk,
Istio/Knative/KServe, and the model-gateway — no deploy script. See
[`ww-overlays/README.md`](ww-overlays/README.md) for the full mechanism.

### 3) Post-deploy: HF token Secret + Tyk key

```bash
# HuggingFace token (used by model init/download containers)
kubectl create secret generic hf-token -n models \
  --from-literal=token="$HF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Issue a Tyk API key to call the gateway — see
[`ww-overlays/post-deploy/README.md`](ww-overlays/post-deploy/README.md).

The gateway image is published to Docker Hub as `rkhoja/aleph` on every push to `main`
touching `gateway/**` (see `.github/workflows/deploy-gateway.yml`). Roll out a new build:

```bash
kubectl rollout restart deploy/model-gateway -n models
```

### 4) Add models

```bash
kubectl apply -f models/<model>/details.yaml          # card (gateway picks it up via watch)
kubectl apply -f models/<model>/inferenceservice.yaml # the KServe ISVC
```

### 5) Test

```bash
# Gateway-level checks (catalog, health, routing guardrails, auth). Add FLEET=1 to
# also warm + probe every model in the catalog (replaces the old full_test sweep).
GW_URL=http://<VIP> TYK_KEY=<key> python3 gateway/test.py

# Per-model feature battery:
GW_URL=http://<VIP> TYK_KEY=<key> MODEL=<id> python3 models/<model>/test.py
```

## 📚 Code Layout

| Path | Description |
|---|---|
| `ww-overlays/` | Warewulf overlays + RKE2 auto-deploy manifests (common / control-plane / gpu-worker), site-value tokens, and post-deploy steps |
| `gateway/` | FastAPI gateway app, translation logic, k8s deployment, Tyk API defs, and `test.py` (model-agnostic gateway checks + optional `FLEET=1` warm-sweep) |
| `models/` | Per-model `InferenceService`, `PVC`, `details.yaml` card, and model-specific test battery |
| `scripts/` | Ops helpers — `test-model.sh` (apply / recreate / up / status / cycle a model) |

## 🧭 Operations Notes

- Main working cluster is HA: 3 control-plane nodes + HAMi-enabled GPU workers (cluster-specific values in `docs/RUNBOOK.md` §0).
- Node image build/publish source-of-truth is [`ualberta-rcg/warewulf-rke2-hami`](https://github.com/ualberta-rcg/warewulf-rke2-hami) (OS, NVIDIA drivers, HAMi runtime, RKE2); this repo's `ww-overlays/` are baked on top of that image per node role.
- Keep secrets in `.env` only (gitignored); do not inline tokens in manifests.
- Model-specific deployment guidance belongs in `models/CLAUDE.md` and optional `models/<model>/CLAUDE.md`.
- Gateway-specific behavior notes belong in `gateway/CLAUDE.md`.

## 🔗 References

- [University of Alberta Research Computing](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html)
- [Alberta Machine Intelligence Institute (AMII)](https://www.amii.ca/)
- [Digital Research Alliance of Canada](https://alliancecan.ca/)
- [HAMi](https://github.com/Project-HAMi/HAMi)
- [Warewulf RKE2 HAMi Image Repo](https://github.com/ualberta-rcg/warewulf-rke2-hami)
- [KServe](https://kserve.github.io/website/latest/)
- [Knative](https://knative.dev/docs/)
- [RKE2](https://docs.rke2.io/)

---

## 🤝 Support

Many Bothans died to bring us this information. This project is provided as-is, but reasonable questions may be answered based on my coffee intake or mood. ;)

Feel free to open an issue or email **[khoja1@ualberta.ca](mailto:khoja1@ualberta.ca)** or **[kali2@ualberta.ca](mailto:kali2@ualberta.ca)** for U of A related deployments.

## 📜 License

This project is released under the **MIT License** - one of the most permissive open-source licenses available.

**What this means:**
- ✅ Use it for anything (personal, commercial, whatever)
- ✅ Modify it however you want
- ✅ Distribute it freely
- ✅ Include it in proprietary software

**The only requirement:** Keep the copyright notice somewhere in your project.

That's it! No other strings attached. The MIT License is trusted by major projects worldwide and removes virtually all legal barriers to using this code.

**Full license text:** [MIT License](./LICENSE)

## 🔭 Why "Aleph"?

The name is borrowed, deliberately, from a few places that all point at the same idea: **one point in space-time that contains all other points.**

- **Borges (1945), *The Aleph*.** A single point in a Buenos Aires cellar that contains every other point in space-time — gaze into it and you see the entire universe at once, from every angle, without overlap or confusion. That is exactly the promise of this platform: *one endpoint that contains every model.* Send a request to a single URL and the whole catalog — 170+ models from protein folders to LLMs — is reachable through that one coordinate.
- **Cantor's mathematics.** ℵ₀ (aleph-null) is the *smallest infinity*, the cardinality of the natural numbers — and the Hebrew letter aleph also means "one." Cantor called it an "infinite unity": countless things, addressed as one. A fitting symbol for a single gateway fronting an unbounded, ever-growing catalog.
- **The latent-space reading.** A modern gloss notes that a model's latent space is itself a kind of Aleph — the whole training corpus compressed into one high-dimensional point, where a prompt is just a coordinate and the output is the view from there. Aleph the platform is the infrastructure layer over many such points.
- **The sci-fi reading.** In Frederik Pohl's *The Gold at the Starbow's End*, **Alpha-Aleph** is the destination — the planet that gives a crew (and a civilization) somewhere to aim. We like that too: a shared place researchers point their jobs at, where the hard part is already running.

*One point. Every model. Infinite unity.*

## 🧠 About University of Alberta Research Computing

The [Research Computing Group](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html) supports high-performance computing, data-intensive research, and advanced infrastructure for researchers at the University of Alberta and across Canada.

We help design and operate compute environments that power innovation — from AI training clusters to national research infrastructure.
