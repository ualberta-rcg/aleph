# qwen36-27b — Model Context

Qwen3.6-27B dense (novel Gated-DeltaNet hybrid architecture). TP2 across 2× L40S. Vision +
tools + toggle thinking.

## Serving
- Image `vllm/vllm-openai:v0.20.2`, **TP2**, `--reasoning-parser qwen3 --tool-call-parser
  qwen3_coder --enable-auto-tool-choice`, `--max-model-len 131072`, `--disable-custom-all-reduce`.
- Whole-device GPUs (`nvidia.com/gpu: "2"`, no `gpumem`); `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`.
- Weights on PVC; `minReplicas: 0` + `scale-to-zero-pod-retention-period: 15m`.

## Gateway integration
- Card `details.yaml`: Template A, `schema_version: 2`, thinking `mode: effort` with
  `enable_thinking` on/off maps. `strips_thinking: false`, `off_max_tokens: 2048`.
- **Managed thinking** — ON (medium/high) exposes the **`reasoning`** field (Anthropic: `thinking`
  block); OFF (`reasoning_effort: none`) → `enable_thinking: false`, no reasoning + capped tokens.
- Binary thinking — a real off (unlike gpt-oss). vLLM v0.20.2 emits reasoning in **`reasoning`**.

## Deploy / test
```bash
kubectl apply -f models/qwen36-27b/
cat models/qwen36-27b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last result: **28 pass / 2 expected / 0 fail** (30-check vision+tools battery: wake + OpenAI/Anthropic
features + thinking on/off/budget/stream + meta-tasks + vision + guardrails).
