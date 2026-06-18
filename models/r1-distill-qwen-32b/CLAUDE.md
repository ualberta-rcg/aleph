# r1-distill-qwen-32b — Model Context

DeepSeek-R1 distilled into Qwen-32B. Always-on reasoning (no toggle). TP2 on 2× L40S.

## Serving
- `vllm/vllm-openai:v0.20.2`, TP2, `--reasoning-parser deepseek_r1`, `--max-model-len 65536`.
- Whole-device GPUs (`nvidia.com/gpu: "2"`); `minReplicas: 0` + 15-min retention.

## Gateway integration
- Card: v2, thinking `mode: always_on` (managed). `strips_thinking: false`, `off_max_tokens: 4096`.
- ON (default) exposes the **`reasoning`** field (Anthropic: `thinking` block); OFF
  (`reasoning_effort: none` / meta-task) strips reasoning + caps `max_tokens`. Meta-task caps are
  generous (always-on thinks a lot, so small caps come back empty).
- vLLM v0.20.2 emits reasoning in **`reasoning`**.

## Deploy / test
```bash
kubectl apply -f models/r1-distill-qwen-32b/
cat models/r1-distill-qwen-32b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last result: **20 pass / 5 expected / 0 fail** (25-check always-on battery).

## Note
- ISVC must have **no** `serving.kserve.io/stop` annotation for wake-on-demand (was pre-stopped; removed).
