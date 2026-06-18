# GLM-4-32B-0414

Zhipu-AI's **GLM-4-32B-0414** — a 32B dense instruct model with strong function-calling and agentic workflows (BFCL-v3 ≈ GPT-4o). Text-only, served across 2× L40S (TP2).
[HuggingFace: THUDM/GLM-4-32B-0414](https://huggingface.co/THUDM/GLM-4-32B-0414) · Apache-2.0

## What it does
- **Tool calling**: native function calling, parsed by a custom `glm4_0414` plugin into OpenAI-compatible `tool_calls`. Well-suited to agents.
- **Context** 32K. Text-only — images rejected with `400 vision_unsupported`.
- No reasoning/thinking mode (use a reasoning model for chain-of-thought).

## Call it
```bash
curl $GW/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "glm-4-32b",
  "messages": [{"role": "user", "content": "What is the weather in Edmonton?"}],
  "tools": [{"type":"function","function":{"name":"get_weather","parameters":{"type":"object","properties":{"city":{"type":"string"}}}}}],
  "max_tokens": 200
}'
```

## Resources
- 2× L40S (whole devices, TP2), `--disable-custom-all-reduce` (PCIe topology), `vllm/vllm-openai:v0.20.2`. Weights ~64 GB on PVC `glm-4-32b-data`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~3 min.

## Source
[HuggingFace: THUDM/GLM-4-32B-0414](https://huggingface.co/THUDM/GLM-4-32B-0414) · Apache-2.0
