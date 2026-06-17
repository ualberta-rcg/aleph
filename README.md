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

The repo includes deployment manifests, model cards, gateway logic, storage configs, install scripts, and validation harnesses used to run the stack reproducibly.

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

### 2) Create HuggingFace token Secret

```bash
kubectl create secret generic hf-token -n models \
  --from-literal=token="$HF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 3) Deploy gateway + models

```bash
# from a login node with sudo SSH access to control plane
./deploy-aleph/deploy.sh

# or pin a CI-built image tag
GATEWAY_IMAGE=rkhoja/aleph:gateway-<sha> ./deploy-aleph/deploy.sh
```

Gateway image is published to Docker Hub as `rkhoja/aleph` (see `.github/workflows/deploy-gateway.yml`).

### 4) Run full compatibility tests

```bash
python3 test/full_test.py
```

## 📚 Repository Layout

| Path | Description |
|---|---|
| `gateway/` | FastAPI gateway app, translation logic, k8s deployment, Tyk API defs |
| `models/` | Per-model `InferenceService`, `PVC`, and `details.yaml` cards |
| `deploy-aleph/` | Platform deploy: install scripts (Istio/Knative/KServe, Tyk), StorageClasses, `deploy.sh` |
| `test/` | Deployment & verification tests (`full_test.py`, `test-model.sh`, `smoke.sh`); fixtures in `test/inputs/` |
| `docs/RUNBOOK.md` | Operations guide — deploy, Tyk wiring, day-2 key mgmt, gotchas |
| `docs/GATEWAY-DESIGN.md` | Gateway design rationale |
| `docs/GATEWAY-ARCHITECTURE.md` | Card schema + handler map |
| `CHANGELOG.md` | Timeline of model/platform updates |
| `CLAUDE.md` | Operator and agent context for this repository |

## 🧭 Operations Notes

- Main working cluster is a control-plane node with HAMi-enabled GPU workers (cluster-specific values in `docs/RUNBOOK.md` §0).
- Node image build/publish source-of-truth is [`ualberta-rcg/warewulf-rke2-hami`](https://github.com/ualberta-rcg/warewulf-rke2-hami); this repo consumes that image line.
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
