# geogalactica

**Type**: Chat LLM (30B dense, vLLM, 2x GPU)
**Model**: geobrain-ai/geogalactica
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: vLLM v0.20.2 on 2x L40S (TP=2)

## Naming
- Card id: `geogalactica`
- ISVC name: `geogalactica`
- PVC: `geogalactica` (from ISVC volumes)
- served-model-name: `geogalactica`
- All names match — no `upstream_model_id` mapping needed.

## Key details
- 30B dense, OPT-style architecture (GPT2LMHeadModel, 48 layers, 56 heads, hidden=7168).
- Geoscience domain — further pre-trained Galactica on 65B geo tokens.
- Expert at geoscience Q&A, geology, mineralogy, earth science.
- vLLM v0.20.2, TP=2 (uses 2 of 4 L40S), whole-device GPUs (no gpumem).
- `--disable-custom-all-reduce` — L40S PCIe topology, no NVLink/P2P.
- `--trust-remote-code` for OPT/Galactica architecture.
- Custom `chat_template.jinja` mounted from PVC.
- Tools: NOT supported (rejected with 400).
- Vision: NOT supported (rejected with 400).
- System prompts: supported.
- Streaming: Yes (SSE on both OpenAI and Anthropic).
- Reasoning: NOT supported.
- scale_to_zero: true, 15m idle retention.

## ISVC spec (ground truth)
```
image: vllm/vllm-openai:v0.20.2
command: vllm serve /data
args:
  --served-model-name=geogalactica
  --port=8080
  --tensor-parallel-size=2
  --max-model-len=2048
  --dtype=bfloat16
  --gpu-memory-utilization=0.90
  --trust-remote-code
  --disable-custom-all-reduce
  --chat-template=/data/chat_template.jinja
resources:
  limits: cpu=16, memory=48Gi, nvidia.com/gpu=2
  requests: cpu=8, memory=32Gi, nvidia.com/gpu=2
nodeSelector: gpu=on
volumes: geogalactica (PVC), shm (16Gi emptyDir)
```

## Context / VRAM
- **max-model-len: 2048 (2K)** — hard limit from OPT positional embeddings, cannot extend.
- Context window: 2048. max_completion_tokens: 2000. Default max_tokens: 1024.
- gpu-memory-utilization: 0.90 (~86.4GB of 96GB across 2x L40S).
- Model loads ~28 GiB VRAM. Cold start ~7 minutes (13 shards at ~30s each + compile).

## v2 Schema
- Card updated to v2 compact schema with `input_map`/`output_map`.
- `catalog` block for display metadata.
- `behavior` only (no `compatibility`).
- `param_translation.thinking.mode: "none"` (non-reasoning).

## Validation
- 2026-06-10: 14/14 tests passed (standardized test.py through gateway)
- OpenAI: basic chat, system prompt, high temp, low temp, short max_tokens, streaming (SSE), tools rejected, vision rejected, reasoning effort (ignored)
- Anthropic: basic, system, streaming, tools rejected, vision rejected
- Previous "engine core init failed" issue resolved — loads fine on v0.20.2.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata (v2 schema) |
| `inferenceservice.yaml` | ISVC spec: vLLM TP2 + PVC mount |
| `pvc.yaml` | PVC (geogalactica) |
| `chat_template.jinja` | Custom chat template for Galactica/OPT |
| `test.py` | Gateway test script (14 checks) |
| `CLAUDE.md` | This file |
