# Aleph

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-RKE2-blue.svg)](https://www.rke2.io/)
[![GPU Scheduling](https://img.shields.io/badge/GPU-HAMi-76B900.svg)](https://github.com/Project-HAMi/HAMi)
[![Serving](https://img.shields.io/badge/Serving-KServe%20%2B%20Knative-orange.svg)](https://kserve.github.io/website/latest/)

> **RKE2 + Warewulf + HAMi + KServe/Knative inference platform with OpenAI/Anthropic-compatible gateway.**

*Deployed on the University of Alberta / AMII Vulcan environment for multi-model GPU inference.*

**Maintained by:** Rahim Khoja ([khoja1@ualberta.ca](mailto:khoja1@ualberta.ca)) and Karim Ali ([kali2@ualberta.ca](mailto:kali2@ualberta.ca))

---

## 📖 Description

**Aleph** is an inference platform repository for operating a Kubernetes-based model serving stack with fractional GPU scheduling.

It combines:
- **RKE2** for cluster runtime,
- **Warewulf** for stateless node provisioning,
- **HAMi** for vGPU slicing and scheduling,
- **KServe + Knative** for model services and scale-to-zero,
- **Tyk OSS** for key management and API gateway controls,
- **FastAPI gateway** with OpenAI and Anthropic compatible endpoints.

The repo includes the Warewulf overlays + RKE2 auto-deploy manifests (`ww-overlays/`), model cards, gateway logic, and validation harnesses used to run the stack reproducibly. The platform is fully declarative: bake the overlays into the node image, provision, and the cluster brings itself up.

## ✨ Features

- **OpenAI + Anthropic API compatibility** in a single gateway
- **Fractional GPU scheduling** with HAMi (`nvidia.com/gpumem` + `nvidia.com/gpu`)
- **Mixed model catalog**: chat/reasoning, multimodal, embeddings, rerank, TTS, science
- **Scale-to-zero + warmup-aware testing** for Knative-backed services
- **Tyk key management** and model catalog API endpoints
- **NFS-backed model persistence** with OneFS-safe mount options
- **Per-model manifests** with cards, PVCs, and runtime-specific notes

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

# Per-model feature battery (start from the template, keep the sections that apply):
GW_URL=http://<VIP> TYK_KEY=<key> MODEL=<id> python3 models/<model>/test.py
```

## 📚 Repository Layout

| Path | Description |
|---|---|
| `ww-overlays/` | Warewulf overlays + RKE2 auto-deploy manifests (common / control-plane / gpu-worker), site-value tokens, and post-deploy steps |
| `gateway/` | FastAPI gateway app, translation logic, k8s deployment, Tyk API defs, and `test.py` (model-agnostic gateway checks + optional `FLEET=1` warm-sweep) |
| `models/` | Per-model `InferenceService`, `PVC`, `details.yaml` card, and `test.py` battery (copy `models/test.template.py`) |
| `scripts/` | Ops helpers — `test-model.sh` (apply / recreate / up / status / cycle a model) |
| `docs/RUNBOOK.md` | Operations guide — deploy, Tyk wiring, day-2 key mgmt, gotchas |
| `docs/GATEWAY-DESIGN.md` | Gateway design rationale |
| `docs/GATEWAY-ARCHITECTURE.md` | Card schema + handler map |
| `CHANGELOG.md` | Timeline of model/platform updates |
| `CLAUDE.md` | Operator and agent context for this repository |

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

## 🧠 About University of Alberta Research Computing

The [Research Computing Group](https://www.ualberta.ca/en/information-services-and-technology/research-computing/index.html) supports high-performance computing, data-intensive research, and advanced infrastructure for researchers at the University of Alberta and across Canada.

We help design and operate compute environments that power innovation — from AI training clusters to national research infrastructure.
