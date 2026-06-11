# deepseek-v2-lite-16b

**Type**: Chat LLM (16B MoE, vLLM, GPU)
**Model**: deepseek-ai/DeepSeek-V2-Lite-Chat
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: vLLM v0.20.2 on HAMi GPU slice (1x L40S)

## Naming
- Card id: `deepseek-v2-lite-16b`
- ISVC name: `deepseek-v2-lite-16b`
- PVC: `deepseek-v2-lite-16b`
- served-model-name: `deepseek-v2-lite-16b`
- All names match — no `upstream_model_id` mapping needed.

## Key details
- 15.7B total params (2.4B active), MoE with Multi-head Latent Attention (MLA).
- Bilingual English/Chinese. Strong at reasoning and code.
- vLLM v0.20.2 backend, 1x HAMi GPU slice.
- Supports system prompts, streaming.
- Tools: NOT supported (rejected with 400).
- Vision: NOT supported (rejected with 400).
- scale_to_zero: true, 15m idle retention.

## Context / VRAM
- **max-model-len: 131072 (128K)** — model supports 128K with YaRN.
- Context window: 131072. max_completion_tokens: 8000. Default max_tokens: 4096.
- gpu-memory-utilization: 0.90 (~43.2GB of 48GB L40S).
- MLA KV compression: ~30.4 KB/token, ~14.3GB available for KV = ~481K tokens capacity.
- At 128K context with 3x KV headroom: 393K tokens, 11.4GB — fits comfortably.

## v2 Schema
- Card updated to v2 compact schema with `input_map`/`output_map`.
- `catalog` block for display metadata.
- `behavior` only (no `compatibility`).
- `param_translation.thinking.mode: "none"` (non-reasoning).

## Validation
- 2026-06-10: 14/14 tests passed (8K context)
- 2026-06-10: 14/14 tests passed (128K context) — after upgrading max-model-len

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata (v2 schema) |
| `inferenceservice.yaml` | ISVC spec: vLLM container + PVC mount |
| `pvc.yaml` | PVC (deepseek-v2-lite-16b) |
| `test.py` | Gateway test script |
| `CLAUDE.md` | This file |
