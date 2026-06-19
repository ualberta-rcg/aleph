# R1-Distill-Qwen-32B

DeepSeek-R1 reasoning distilled into Qwen-32B — always-on chain-of-thought. TP2 on 2× L40S.

## What it does
- **Reasoning**: always-on (deepseek_r1 parser, `<think>` blocks). No toggle.
- **No tools**, text-only.
- **Context**: deployed at 64K.

## Thinking, through the gateway
Managed **always-on**: ON (default) exposes the **`reasoning`** field / Anthropic **`thinking`** block.
OFF (`reasoning_effort: none` / meta-task) **strips** the reasoning + caps `max_tokens` (the model
still thinks internally, so content needs adequate `max_tokens`).

## Resources
- 2× L40S (whole devices), TP2, `vllm/vllm-openai:v0.20.2`, `--reasoning-parser deepseek_r1`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~2–3 min.

## Testing
The 26-check always-on battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
cat models/r1-distill-qwen-32b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **21 PASS / 5 EXP / 0 FAIL** — always-on reasoning exposed by default,
stripped + off-capped on `none`/meta, streaming reasoning, stop/system, tools-rejected +
vision-rejected guards, Anthropic parity. (`stop_seq` uses a 2048 budget — the reasoner burns tokens
on CoT before reaching the stop token.)

## Source
[deepseek-ai/DeepSeek-R1-Distill-Qwen-32B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B)
