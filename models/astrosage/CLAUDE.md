# astrosage

**Type**: Chat LLM (8B dense, custom transformers server, 1x GPU slice)
**Model**: AstroMLab/AstroSage-8B
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: Custom FastAPI server (transformers `pipeline("text-generation")`) on 1x L40S vGPU slice

## Naming
- Card id: `astrosage`
- ISVC name: `astrosage`
- PVC: `astrosage-data` (NFS, ReadWriteMany)
- served-model-name: `astrosage`
- All names match — no `upstream_model_id` mapping needed.

## Key details
- 8B dense, Llama-3.1-8B fine-tuned on 250K+ arXiv astronomy papers + 8.8M QA pairs.
- Beats GPT-4o on astronomy benchmarks (80.9% vs 80.4%).
- Custom FastAPI server (NOT vLLM) — `python:3.11-slim` + transformers + torch.
- Server code embedded in ConfigMap `astrosage-server`, mounted at `/app/server.py`.
- Init container creates venv on PVC, downloads model from HF.
- HAMi vGPU slice: `nvidia.com/gpu: 1, nvidia.com/gpumem: 16384` (16GB of 48GB L40S).
- No streaming — `no_stream: true` in gateway routing. Server doesn't support SSE.
- Tools: NOT supported (rejected with 400 by gateway).
- Vision: NOT supported (rejected with 400 by gateway, since gateway-9ade05f).
- System prompts: supported.
- Reasoning: NOT supported.
- scale_to_zero: true, 15m idle retention.
- Health endpoint: `/health` (custom, not `/v1/models`).

## ISVC spec (ground truth)
```
image: python:3.11-slim
command: /data/venv/bin/python /app/server.py
env: MODEL_DIR=/data/model, HF_HOME=/data/hf_cache
initContainers:
  - setup: python:3.11-slim
    - Creates venv (torch, transformers, fastapi, uvicorn) on PVC
    - Downloads AstroSage-8B from HF if not cached
resources:
  limits: cpu=8, memory=24Gi, nvidia.com/gpu=1, nvidia.com/gpumem=16384
  requests: cpu=4, memory=16Gi, nvidia.com/gpu=1, nvidia.com/gpumem=16384
nodeSelector: gpu=on
volumes: astrosage-data (NFS PVC, 25Gi, ReadWriteMany), app (ConfigMap astrosage-server)
readinessProbe: /health, initialDelaySeconds=120, periodSeconds=30
startupProbe: /health, initialDelaySeconds=60, periodSeconds=20
```

## Context / VRAM
- **Context window: 8192 tokens** (Llama-3.1-8B default).
- max_completion_tokens: 8000. Default max_tokens: 512 (server default).
- vGPU slice: 16GB of 48GB L40S. Model ~16GB BF16. Tight fit.
- Cold start: ~2-3 min (venv cached, model load ~30s for 291 shards).

## v2 Schema
- Card updated to v2 compact schema with `input_map`/`output_map`.
- `catalog` block for display metadata.
- `behavior` with all flags set (no tools, no vision, no streaming, no reasoning).
- `routing.no_stream: true` — gateway forces non-streaming response.
- `param_translation.thinking.mode: "none"` (non-reasoning).

## Validation
- 2026-06-10: 14/14 tests passed (standardized test.py through gateway, image gateway-9ade05f)
- OpenAI: basic chat, system prompt, high temp, low temp, short max_tokens, streaming (JSON, no_stream=true), tools rejected (400), vision rejected (400, gateway gate), reasoning effort (ignored)
- Anthropic: basic, system, streaming (non-SSE, no_stream=true), tools rejected (400), vision rejected (400, gateway gate)
- Vision gating added to gateway in this test cycle — previously non-vLLM models passed vision content through.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata (v2 schema) |
| `inferenceservice.yaml` | ISVC spec + embedded ConfigMap (server.py) + PVC |
| `pvc.yaml` | NFS-based PVC (astrosage-data, ReadWriteMany, 25Gi) |
| `test.py` | Gateway test script (14 checks) |
| `CLAUDE.md` | This file |
