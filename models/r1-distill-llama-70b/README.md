# R1-Distill-Llama-70B

DeepSeek-R1 reasoning distilled into Llama-70B — always-on chain-of-thought. TP4 across the whole
4-GPU node.

## What it does
- **Reasoning**: always-on (deepseek_r1 parser, `<think>` blocks). No toggle.
- **No tools**, text-only.
- **Context**: deployed at 64K.

## Thinking, through the gateway
Managed **always-on**: ON (default) exposes the **`reasoning`** field / Anthropic **`thinking`** block.
OFF (`reasoning_effort: none` / meta-task) **strips** the reasoning + caps `max_tokens`.

## Resources
- 4× L40S (whole node), TP4, `vllm/vllm-openai:v0.20.2`, `--reasoning-parser deepseek_r1`.
- `tokenizer_class` patched (fixes Ġ/Ċ garbling). Scale-to-zero 15-min; cold start ~4–5 min.
- Takes the whole GPU node — can't coexist with other whole-GPU models.

## Source
[deepseek-ai/DeepSeek-R1-Distill-Llama-70B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-70B)
