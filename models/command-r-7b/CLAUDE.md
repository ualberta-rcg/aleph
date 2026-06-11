# command-r-7b

**Type**: Chat LLM (7B, vLLM, GPU)
**Model**: CohereForAI/c4ai-command-r7b-12-2024
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: vLLM on HAMi GPU slice

## Naming
- Card id: `command-r-7b`
- ISVC name: `command-r-7b`
- PVC: `command-r-7b-data`
- served-model-name: `command-r-7b`
- All names match — no `upstream_model_id` mapping needed.

## Key details
- 7B parameter RAG-optimized multilingual chat model from Cohere.
- vLLM backend, GPU slice via HAMi.
- Supports system prompts, streaming.
- Tools: NOT supported (rejected with 400).
- Vision: NOT supported (rejected with 400).
- Custom params: top_p, top_k, repetition_penalty (passthrough).
- scale_to_zero: true, 15m idle retention.

## Validation (2026-06-10)
- 16/16 tests passed through gateway
- OpenAI: basic chat, system prompt, high/low temp, short max_tokens, streaming, tools rejected, vision rejected, reasoning effort ignored, custom params (top_p, repetition_penalty)
- Anthropic: basic, system, streaming, tools rejected, vision rejected
