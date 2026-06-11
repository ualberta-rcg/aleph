# openbiollm-70b

**Type**: Chat LLM (70B, vLLM, 4x GPU)
**Model**: aaditya/Llama3-OpenBioLLM-70B
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: vLLM v0.20.2 on 4x L40S (TP=4)

## Naming
- Card id: `openbiollm-70b`
- ISVC name: `openbiollm-70b`
- PVC: `openbiollm-70b-data`
- served-model-name: `openbiollm-70b`
- All names match — no `upstream_model_id` mapping needed.

## Key details
- Llama 3 70B fine-tuned on biomedical data (PubMed, clinical texts).
- Strong at medical Q&A, clinical reasoning, biomedical NLP.
- vLLM v0.20.2, **TP=4** — uses ALL 4 L40S GPUs. No other GPU model can run simultaneously.
- Supports system prompts, streaming.
- Tools: NOT supported (rejected with 400).
- Vision: NOT supported (rejected with 400).
- scale_to_zero: true, 15m idle retention.
- Cold start: ~7 minutes (30 checkpoint shards, ~393s load time).

## Context / VRAM
- **Context: 8192 (8K)** — native max. Llama 3 70B base, `rope_scaling: null`, no YaRN.
- **max-model-len: 8192**. Cannot safely extend beyond 8K.
- 4x L40S = 192GB. Model weights ~133GB (bf16). KV capacity ~47GB = ~151K tokens.
- At 8K context with 3x KV = 24K tokens = 7.5GB — only 16% of KV capacity. Very comfortable.

## v2 Schema
- Card updated to v2 compact schema with `input_map`/`output_map`.
- `catalog` block for display metadata.
- `behavior` only (no `compatibility`).

## Validation
- 2026-06-10: 14/14 tests passed through gateway
- OpenAI: basic chat, system prompt, high/low temp, short max_tokens, streaming, tools rejected, vision rejected, reasoning effort ignored
- Anthropic: basic, system, streaming, tools rejected, vision rejected

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata (v2 schema) |
| `inferenceservice.yaml` | ISVC spec: vLLM TP4 + PVC mount + shared memory |
| `pvc.yaml` | PVC (openbiollm-70b-data) |
| `download-job.yaml` | Job to download model to PVC |
| `test.py` | Gateway test script |
| `CLAUDE.md` | This file |
