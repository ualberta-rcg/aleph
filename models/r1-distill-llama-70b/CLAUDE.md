# r1-distill-llama-70b — Model Context

DeepSeek-R1 distilled into Llama-70B. Always-on reasoning (no toggle). TP4 across the whole GPU node.

## Serving
- `vllm/vllm-openai:v0.20.2`, TP4, `--reasoning-parser deepseek_r1`, `--max-model-len 65536`.
- Whole-node GPUs (`nvidia.com/gpu: "4"`); `tokenizer_class` patch (fixes Ġ/Ċ garbling).
- `minReplicas: 0` + 15-min retention. Takes all 4 GPUs — exclusive.

## Gateway integration
- Card: v2, thinking `mode: always_on` (managed). `strips_thinking: false`, `off_max_tokens: 4096`.
- ON (default) exposes the **`reasoning`** field (Anthropic: `thinking` block); OFF strips + caps.
- vLLM v0.20.2 emits reasoning in **`reasoning`**.

## Deploy / test
```bash
kubectl apply -f models/r1-distill-llama-70b/
cat models/r1-distill-llama-70b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last result: **20 pass / 5 expected / 0 fail** (25-check always-on battery).
