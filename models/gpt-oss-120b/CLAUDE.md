# gpt-oss-120b — Model Context

Large OpenAI reasoning model (117B MoE, MXFP4). Served by vLLM across 2× L40S (tensor-parallel 2). The cluster's flagship reasoning model and the **reference exemplar** for a working managed-thinking model (correct card + full feature verification).

## Serving
- Image `vllm/vllm-openai:v0.20.2`, **TP2**, `--reasoning-parser openai_gptoss --tool-call-parser openai --enable-auto-tool-choice`, `--max-model-len 131072`, `--disable-custom-all-reduce`.
- Whole-device GPUs (`nvidia.com/gpu: "2"`, **no `gpumem`**) — requesting `gpumem` would trigger HAMi vGPU mode and break multi-GPU P2P. `--disable-custom-all-reduce` because L40S TP≥2 is PCIe/CPU topology (no NVLink P2P); vLLM's custom all-reduce busy-waits there, NCCL fallback is correct + fast.
- Attention backend left **auto** (per the proven POC config; TRITON is selected natively on SM89).
- Weights ~60 GB on PVC at `/data`; shared memory 16 Gi. `minReplicas: 0` + `scale-to-zero-pod-retention-period: 15m`.

## Gateway integration
- Card `details.yaml`: Template A, `schema_version: 2`, thinking `mode: effort`. Listed in `DETAILS-TEMPLATE-LLM.md` as the "Complex (tools+vision)" exemplar.
- **Managed thinking** — ON exposes the **`reasoning`** field (Anthropic: `thinking` block); OFF (`reasoning_effort: none`) strips it + caps `max_tokens` to `off_max_tokens` (2048). `behavior.strips_thinking: false`.
- vLLM v0.20.2 emits reasoning in **`reasoning`** (not `reasoning_content`) — the gateway reads either.

## Deploy / test
```bash
kubectl apply -f models/gpt-oss-120b/      # details.yaml + inferenceservice.yaml + pvc.yaml
# run the 33-check battery inside the gateway pod:
cat models/gpt-oss-120b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last result: **30 pass / 3 expected / 0 fail** (wake + OpenAI/Anthropic features + thinking on/off/budget/stream + meta-tasks + guardrails).

## Notes
- gpt-oss always reasons internally — "off" = lowest effort (`low`) + stripped/capped output, not true no-reasoning.
- High effort is token-voracious: give adequate `max_tokens` or the answer comes back empty (all budget spent on reasoning).
- Scheduling: TP2 takes 2 whole GPUs — cannot run alongside another whole-GPU model on the same 4-GPU node.
