# Models Deployment Guide

This file describes the standard process for adding/updating model deployments under `models/`.

## Directory contract

Each model directory should contain (as applicable):
- `details.yaml` — model card metadata used by the gateway catalog
- `inferenceservice.yaml` — KServe runtime spec
- `pvc.yaml` — persistent storage claim for weights/cache
- optional extras: `download-job.yaml`, `server-configmap.yaml`, helper scripts
- optional local notes: `CLAUDE.md` for model-specific quirks

## Before you deploy a model

1. Verify model/task fit and expected context/tool support from upstream docs.
2. Choose runtime type:
   - vLLM (`vllm/vllm-openai:v0.20.2`) for chat/reasoning multimodal LLMs
   - TEI for embeddings/rerank where appropriate
   - custom python server for special science/TTS models
3. Decide scaling mode:
   - `minReplicas: 0` for scale-to-zero services
   - `minReplicas: 1` for always-on low-latency services
4. Set compute resources (CPU/memory can be generous; GPU must be deliberate).
5. Ensure secrets are referenced from k8s Secret, never inline tokens.

## GPU/HAMi conventions

- GPU workloads require node selector `gpu: "on"`.
- **Single-GPU / fractional models (TP=1):** use HAMi vGPU sharing:
  - `nvidia.com/gpumem: "<MiB>"` + `nvidia.com/gpu: "1"`.
- **Multi-GPU models (tensor-parallel ≥ 2): DO NOT request `nvidia.com/gpumem`.**
  Required recipe for TP≥2 on this cluster (exactly TWO things needed):
  - request whole devices: `nvidia.com/gpu: "<N>"` and **no** `nvidia.com/gpumem`
    (HAMi then binds N tenant-free physical cards; each vGPU defaults to full card mem)
  - vLLM arg `--disable-custom-all-reduce` (fall back to NCCL → native speed)
- **Why `--disable-custom-all-reduce` is mandatory (hardware, not HAMi):** the L40S
  cards here are NODE topology (PCIe via CPU, no NVLink, no working GPU P2P). vLLM's
  custom all-reduce assumes P2P and **hangs at engine init** — verified cleanly:
  oceangpt-30b TP2 on *whole devices, no gpumem, no CUDA_DISABLE_CONTROL* but WITHOUT
  the flag hung >7 min at engine startup (repeating "No available shared memory
  broadcast block / processes hanging"); WITH the flag it serves in ~2.5 min at
  ~73 tok/s. NCCL (the fallback) works fine. This is NOT a gpumem/vGPU artifact.
- **`CUDA_DISABLE_CONTROL` is NOT required** — verified; no-gpumem already gives
  whole-card memory and native behavior.
- The fix took gpt-oss-120b from 0.25 → ~200 tok/s. Validated TP2 (oceangpt ~73,
  medgemma ~20) and TP4 (qwen35-122b ~65). The legacy POC cluster doesn't need any of
  this because it uses the NVIDIA GPU Operator (whole devices, native P2P), not HAMi.
- **VRAM guard (bash `nvidia-smi memory.free` retry loop) is now redundant** for
  whole-device models: HAMi only schedules them onto tenant-free cards, so VRAM is
  always free on first check. Harmless to keep, fine to drop.
- **vLLM image is standardized to `vllm/vllm-openai:v0.20.2`** for all LLMs (matches 232).
- Do NOT add `--kv-cache-dtype fp8` or `--enable-prefix-caching` to gpt-oss models:
  attention sinks break under fp8, and TP>1 + prefix-caching can yield empty responses.

## Storage conventions

- Use `storageClassName: nfs-client` unless an exception is documented.
- Keep weights on PVC so cold starts avoid repeated downloads.
- Init containers should short-circuit if model artifacts already exist.

## Required secret setup

Expected Secret in namespace `models`:

```bash
kubectl create secret generic hf-token -n models \
  --from-literal=token="$HF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Manifests should use:

```yaml
- name: HF_TOKEN
  valueFrom:
    secretKeyRef:
      name: hf-token
      key: token
```

## Deploy sequence (per model)

1. `kubectl apply -f models/<name>/pvc.yaml` (if present)
2. `kubectl apply -f models/<name>/server-configmap.yaml` (if present)
3. `kubectl apply -f models/<name>/inferenceservice.yaml`
4. wait for readiness / revision availability
5. run smoke tests through gateway endpoint and direct backend if needed
6. update `details.yaml` to reflect real capabilities and caveats

## Validation checklist

- OpenAI path works (`/v1/chat/completions` or `/v1/embeddings`)
- Anthropic path works for chat-capable models (`/v1/messages`)
- Tool support matches reality (`supports_tools` true/false)
- Reasoning behavior validated (including stripping policy where enabled)
- Context-window expectations documented in `details.yaml`

## Optional per-model notes

If a model has quirks, add `models/<model>/CLAUDE.md`.
Use `models/CLAUDE-TEMPLATE.md` as the starter format.
