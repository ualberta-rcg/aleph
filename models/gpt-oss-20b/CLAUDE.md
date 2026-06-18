# gpt-oss-20b — Model Context

Lightweight OpenAI reasoning model (21B MoE). Served by vLLM on one L40S vGPU slice.

## Serving
- Image `vllm/vllm-openai:v0.20.2`, **TP1**, `--reasoning-parser openai_gptoss --tool-call-parser openai --enable-auto-tool-choice`, `--max-model-len 131072`.
- `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1` (required on L40S / SM89 — FlashAttention-3 unavailable).
- Weights on NFS PVC at `/data` (skip re-download on cold start); `nvidia.com/gpumem: 24576` (sub-GPU slice).
- `minReplicas: 0` + `scale-to-zero-pod-retention-period: 15m` (scale-to-zero, wake-on-demand).

## Gateway integration
- Card `details.yaml`: Template A, `schema_version: 2`, thinking `mode: effort`.
- **Managed thinking** — ON exposes the **`reasoning`** field (Anthropic: `thinking` block); OFF (`reasoning_effort: none`) strips it + caps `max_tokens` to `off_max_tokens` (2048). `behavior.strips_thinking: false`.
- vLLM v0.20.2 emits reasoning in **`reasoning`** (not `reasoning_content`) — the gateway reads either.

## Deploy / test
```bash
kubectl apply -f models/gpt-oss-20b/      # details.yaml + inferenceservice.yaml + pvc.yaml
# run the 33-check battery inside the gateway pod:
cat models/gpt-oss-20b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last result: **30 pass / 3 expected / 0 fail** (wake + OpenAI/Anthropic features + thinking on/off/budget/stream + meta-tasks + guardrails).

## Notes
- gpt-oss always reasons internally — "off" = lowest effort (`low`) + stripped/capped output, not true no-reasoning.
- High effort is token-voracious: give adequate `max_tokens` or the answer comes back empty (all budget spent on reasoning).
