# glm-4-32b

**Type**: Chat LLM (32B dense, vLLM, GPU, TP2)
**Model**: THUDM/GLM-4-32B-0414
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: vLLM (TP2) on L40S

## Naming
- Card id: `glm-4-32b`
- ISVC name: `glm-4-32b`
- PVC: `glm-4-32b-data`
- served-model-name: `glm-4-32b`
- All names match — no `upstream_model_id` mapping needed.

## Key details
- 32B dense, strong function-calling + agentic workflows (Zhipu-AI).
- vLLM backend, TP2 across 2x L40S (~64 GB weights).
- Supports system prompts, streaming, function-calling tools.
- Tools: supported. Vision: NOT supported (rejected with 400). Reasoning: no.
- Custom params: top_p, top_k, temperature (passthrough).
- scale_to_zero: true, 15m idle retention.

## Validation (2026-06-18)
- Comprehensive gateway battery (`test.py`): see run logs.
- OpenAI: basic, system, temp/top_k, stop, max_tokens, usage, resources, streaming, tools work.
- Anthropic: basic, system, temp, stop_sequences, streaming.
