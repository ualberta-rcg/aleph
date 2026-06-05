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
- Fractional allocations use:
  - `nvidia.com/gpumem: "<MiB>"`
  - `nvidia.com/gpu: "1"` (or higher if tensor parallel/full GPU)
- For multi-GPU large models, request explicit GPU count and enough gpumem.

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
