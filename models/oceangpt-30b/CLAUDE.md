# oceangpt-30b

**Type**: Chat LLM (30B MoE, vLLM, 2x GPU)
**Model**: zjunlp/OceanGPT-basic-30B-A3B-Instruct
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: vLLM v0.20.2 on 2x L40S (TP=2)

## Naming
- Card id: `oceangpt-30b`
- ISVC name: `oceangpt-30b`
- PVC: `oceangpt-30b-data`
- served-model-name: `oceangpt-30b`
- All names match — no `upstream_model_id` mapping needed.

## Key details
- 30.5B total params (3B active), Qwen3 MoE architecture (128 experts, 8 active per token).
- Ocean/marine science domain. Bilingual EN/ZH.
- Trained on marine biology, oceanography, climate, fisheries data.
- System prompt: "你是海洋知识专家" (marine knowledge expert).
- vLLM v0.20.2, TP=2 (uses 2 of 4 L40S), whole-device GPUs (no gpumem).
- `--disable-custom-all-reduce` — L40S PCIe topology, no NVLink/P2P.
- `--trust-remote-code` — required for Qwen3 MoE architecture.
- **Tools: SUPPORTED** (`--tool-call-parser=hermes` + `--enable-auto-tool-choice`). Works on both OpenAI and Anthropic endpoints.
- Streaming: Yes (SSE on both OpenAI and Anthropic).
- Vision: NOT supported (rejected with 400).
- System prompts: supported.
- Multi-turn: supported.
- Reasoning: NOT supported (not a reasoning model).
- scale_to_zero: true, 15m idle retention.

## ISVC spec (ground truth)
```
image: vllm/vllm-openai:v0.20.2
command: vllm serve /data
args:
  --served-model-name=oceangpt-30b
  --port=8080
  --tensor-parallel-size=2
  --max-model-len=65536
  --dtype=bfloat16
  --gpu-memory-utilization=0.90
  --trust-remote-code
  --disable-custom-all-reduce
  --tool-call-parser=hermes
  --enable-auto-tool-choice
resources:
  limits: cpu=16, memory=48Gi, nvidia.com/gpu=2
  requests: cpu=8, memory=32Gi, nvidia.com/gpu=2
nodeSelector: gpu=on
volumes: oceangpt-30b-data (PVC), shm (16Gi emptyDir)
```

## Context / VRAM
- **max-model-len: 65536 (64K)** — model supports 262K native, limited to 64K on 2x L40S.
- Context window: 65536. max_completion_tokens: 64000. Default max_tokens: 4096.
- gpu-memory-utilization: 0.90 (~86.4GB of 96GB across 2x L40S).
- 4.2x KV headroom at 64K context on TP2.

## v2 Schema
- Card updated to v2 compact schema with `input_map`/`output_map`.
- `catalog` block for display metadata.
- `behavior` only (no `compatibility`).
- `param_translation.thinking.mode: "none"` (non-reasoning).

## Validation
- 2026-06-10: 14/14 tests passed (standardized test.py through gateway)
- OpenAI: basic chat, system prompt (Chinese), high temp, low temp, short max_tokens, streaming (SSE), tools (`get_sea_temperature` tool_calls), vision rejected, reasoning effort (ignored)
- Anthropic: basic, system, streaming, tools (`get_sea_temperature` tool_use), vision rejected

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata (v2 schema) |
| `inferenceservice.yaml` | ISVC spec: vLLM TP2 + PVC mount |
| `pvc.yaml` | PVC (oceangpt-30b-data) |
| `test.py` | Gateway test script (14 checks) |
| `CLAUDE.md` | This file |
